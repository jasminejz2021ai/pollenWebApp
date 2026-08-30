import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import {
  MapContainer, ImageOverlay, Polygon, Popup,
  useMap, useMapEvents, ZoomControl, Tooltip,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import '@geoman-io/leaflet-geoman-free';
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css';
import type { HeatmapResponse, FloraItem, Building, Campus } from '../utils/api';

interface CampusMapProps {
  heatmap: HeatmapResponse | null;
  flora: FloraItem[];
  buildings: Building[];
  campus: Campus | null;
  onTreeSelect: (tree: FloraItem) => void;
}

const CAMPUS_CENTER: [number, number] = [37.4012, -122.1340];

// Geographic extent of the satellite background image. This is the single
// source of truth: the map must never display an area larger than this, so we
// clamp panning to these bounds and compute a minZoom that keeps the image
// filling the viewport (no black/empty borders when zoomed out).
const SATELLITE_BOUNDS: [[number, number], [number, number]] = [
  [37.3988, -122.1372],
  [37.4038, -122.1300],
];

const METERS_PER_DEG_LAT = 111320;

// Build a rotated rectangle footprint from center, width (E-W, m), length
// (N-S, m), and rotation (degrees clockwise). Returns closed [lat,lng] ring.
function rotatedRect(
  lat: number, lng: number, width_m: number, length_m: number, angle_deg: number,
): [number, number][] {
  const mLat = METERS_PER_DEG_LAT;
  const mLng = METERS_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180);
  const hw = width_m / 2;
  const hl = length_m / 2;
  const a = (angle_deg * Math.PI) / 180;
  const cos = Math.cos(a), sin = Math.sin(a);
  // Local corners (x=E, y=N) before rotation
  const corners: [number, number][] = [
    [-hw, -hl], [hw, -hl], [hw, hl], [-hw, hl],
  ];
  const ring = corners.map(([x, y]) => {
    const rx = x * cos - y * sin;
    const ry = x * sin + y * cos;
    return [lat + ry / mLat, lng + rx / mLng] as [number, number];
  });
  ring.push(ring[0]);
  return ring;
}

// Campus boundary - rotated 25° to align with Arastradero Rd
const CAMPUS_BOUNDARY: [number, number][] = [
  [37.398454, -122.135770],
  [37.401159, -122.129970],
  [37.405146, -122.131830],
  [37.402441, -122.137630],
  [37.398454, -122.135770],
];

interface DetectedFeature {
  lat: number;
  lng: number;
  polygon: [number, number][];
  type: 'tree' | 'building';
  radius_m?: number;
  width_m?: number;
  height_m?: number;
  length_m?: number;
  angle_deg?: number;
  name?: string;
  floors?: number;
  species_key?: string;
}

const SPECIES_INFO: Record<string, { name: string; scientific: string; family: string; potency: number }> = {
  palm: { name: "Canary Island Date Palm", scientific: "Phoenix canariensis", family: "Arecaceae", potency: 3.0 },
  valley_oak: { name: "Valley Oak", scientific: "Quercus lobata", family: "Fagaceae", potency: 4.5 },
  coast_live_oak: { name: "Coast Live Oak", scientific: "Quercus agrifolia", family: "Fagaceae", potency: 4.0 },
  redwood: { name: "Coast Redwood", scientific: "Sequoia sempervirens", family: "Cupressaceae", potency: 2.5 },
  eucalyptus: { name: "Eucalyptus", scientific: "Eucalyptus spp.", family: "Myrtaceae", potency: 2.0 },
  pine: { name: "Pine", scientific: "Pinus spp.", family: "Pinaceae", potency: 2.0 },
  chinese_elm: { name: "Chinese Elm", scientific: "Ulmus parvifolia", family: "Ulmaceae", potency: 3.0 },
  sycamore: { name: "Western Sycamore", scientific: "Platanus racemosa", family: "Platanaceae", potency: 3.5 },
  perennial_grass: { name: "Turf Grass", scientific: "Poaceae spp.", family: "Poaceae", potency: 4.0 },
};

function HeatmapOverlay({ heatmap, visible, bounds, buildings }: { heatmap: HeatmapResponse | null; visible: boolean; bounds: [[number, number], [number, number]]; buildings: DetectedFeature[] }) {
  const map = useMap();
  const overlayRef = useRef<L.ImageOverlay | null>(null);

  useEffect(() => {
    if (overlayRef.current) { map.removeLayer(overlayRef.current); overlayRef.current = null; }
    if (!visible || !heatmap || !heatmap.points.length) return;

    const llBounds = L.latLngBounds(bounds);
    const canvas = document.createElement('canvas');
    canvas.width = 500; canvas.height = 500;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const south = llBounds.getSouth(), north = llBounds.getNorth();
    const west = llBounds.getWest(), east = llBounds.getEast();

    heatmap.points.forEach((p) => {
      const px = ((p.lng - west) / (east - west)) * 500;
      const py = ((north - p.lat) / (north - south)) * 500;
      const radius = 20 + p.weight * 22;
      const gradient = ctx.createRadialGradient(px, py, 0, px, py, radius);
      if (p.weight > 0.7) {
        gradient.addColorStop(0, 'rgba(220, 38, 38, 0.6)');
        gradient.addColorStop(0.4, 'rgba(249, 115, 22, 0.35)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else if (p.weight > 0.3) {
        gradient.addColorStop(0, 'rgba(249, 115, 22, 0.4)');
        gradient.addColorStop(0.5, 'rgba(250, 204, 21, 0.2)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else {
        gradient.addColorStop(0, 'rgba(250, 204, 21, 0.2)');
        gradient.addColorStop(0.6, 'rgba(34, 197, 94, 0.1)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      }
      ctx.beginPath(); ctx.fillStyle = gradient;
      ctx.arc(px, py, radius, 0, Math.PI * 2); ctx.fill();
    });

    // Punch out building footprints: no outdoor pollen exposure at breathing
    // height inside a building. Clearing here prevents neighboring points'
    // radial gradients from bleeding color over the rooftops.
    if (buildings && buildings.length) {
      ctx.save();
      ctx.globalCompositeOperation = 'destination-out';
      ctx.fillStyle = 'rgba(0,0,0,1)';
      for (const b of buildings) {
        const poly = b.polygon as [number, number][];
        if (!poly || poly.length < 3) continue;
        ctx.beginPath();
        poly.forEach(([lat, lng], i) => {
          const bx = ((lng - west) / (east - west)) * 500;
          const by = ((north - lat) / (north - south)) * 500;
          if (i === 0) ctx.moveTo(bx, by); else ctx.lineTo(bx, by);
        });
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
    }

    const overlay = L.imageOverlay(canvas.toDataURL(), llBounds, { opacity: 0.7, interactive: false });
    overlay.addTo(map);
    overlayRef.current = overlay;
    return () => { if (overlayRef.current) { map.removeLayer(overlayRef.current); overlayRef.current = null; } };
  }, [heatmap, visible, map, bounds, buildings]);
  return null;
}

// Ensures the ENTIRE satellite image is always visible. It computes the zoom
// at which SATELLITE_BOUNDS fully fits inside the map container, enforces that
// as the maximum zoom-out (minZoom), and recomputes on resize. Any leftover
// margin (when the window aspect differs from the image) is covered by the
// map container's background color rather than a black band.
function FitImageBounds({ bounds }: { bounds: [[number, number], [number, number]] }) {
  const map = useMap();

  useEffect(() => {
    const llBounds = L.latLngBounds(bounds);

    const applyFill = () => {
      // Container must have its real size before getBoundsZoom is meaningful.
      map.invalidateSize({ animate: false });
      const fitZoom = map.getBoundsZoom(llBounds, false);
      const fillZoom = map.getBoundsZoom(llBounds, true);
      map.setMinZoom(fitZoom);
      // Recenter on the image and zoom so it covers the full viewport (no
      // black strips). Applied repeatedly during the settle window below so a
      // still-sizing container on first load can't leave the image too small.
      map.setView(llBounds.getCenter(), fillZoom, { animate: false });
    };

    // Apply immediately when ready, then again across a short settle window to
    // catch the container reaching its final size on first load (the cause of
    // the black strips that appeared on the default campus).
    map.whenReady(applyFill);
    const raf = requestAnimationFrame(applyFill);
    const timers = [50, 150, 400, 800].map((ms) => setTimeout(applyFill, ms));

    // After the settle window, stop force-centering so the user can pan/zoom
    // freely; only enforce the zoom-out floor on later resizes.
    const onResize = () => {
      map.invalidateSize({ animate: false });
      const fitZoom = map.getBoundsZoom(llBounds, false);
      const fillZoom = map.getBoundsZoom(llBounds, true);
      map.setMinZoom(fitZoom);
      if (map.getZoom() < fillZoom) {
        map.setView(llBounds.getCenter(), fillZoom, { animate: false });
      }
    };
    const resizeTimer = setTimeout(() => map.on('resize', onResize), 900);

    return () => {
      cancelAnimationFrame(raf);
      timers.forEach(clearTimeout);
      clearTimeout(resizeTimer);
      map.off('resize', onResize);
    };
  }, [map, bounds]);

  return null;
}

// In "add building" mode, a map click places a new building centered at the
// clicked point. Disabled otherwise so normal clicks (popups) still work.
function AddBuildingHandler({
  active, onAdd,
}: { active: boolean; onAdd: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      if (active) onAdd(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Derive an oriented rectangle's center, width (m), length (m), and rotation
// (deg) from its corner lat/lngs. Uses the first edge as the "width" axis.
function rectFromCorners(
  corners: [number, number][], baseLat: number,
): { lat: number; lng: number; width_m: number; length_m: number; angle_deg: number } {
  const mLat = METERS_PER_DEG_LAT;
  const mLng = METERS_PER_DEG_LAT * Math.cos((baseLat * Math.PI) / 180);
  // Convert to local meters
  const pts = corners.map(([la, ln]) => [ln * mLng, la * mLat] as [number, number]);
  const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length;
  const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
  // Edge 0->1 and 1->2 give the two side vectors
  const e1x = pts[1][0] - pts[0][0], e1y = pts[1][1] - pts[0][1];
  const e2x = pts[2][0] - pts[1][0], e2y = pts[2][1] - pts[1][1];
  const width_m = Math.hypot(e1x, e1y);
  const length_m = Math.hypot(e2x, e2y);
  const angle_deg = (Math.atan2(e1y, e1x) * 180) / Math.PI;
  const clat = cy / mLat;
  const clng = cx / mLng;
  return { lat: clat, lng: clng, width_m, length_m, angle_deg };
}

// Imperative edit layer: edits ONE selected building at a time. Draws it as a
// Leaflet polygon with Geoman drag/resize plus a draggable rotation handle.
// Editing one shape avoids the churn of managing all buildings at once.
function BuildingEditLayer({
  selectedIndex, building, onChange,
}: {
  selectedIndex: number | null;
  building: DetectedFeature | null;
  onChange: (index: number, patch: Partial<DetectedFeature>) => void;
}) {
  const map = useMap();
  const layersRef = useRef<L.Layer[]>([]);

  useEffect(() => {
    layersRef.current.forEach((l) => map.removeLayer(l));
    layersRef.current = [];
    if (selectedIndex === null || !building || !building.polygon) return;

    const i = selectedIndex;
    const b = building;
    const poly = L.polygon(b.polygon as [number, number][], {
      color: '#f59e0b', weight: 3, fillColor: '#f59e0b', fillOpacity: 0.35,
    }).addTo(map);
    layersRef.current.push(poly);

    // Show vertex + edge markers for resizing, and allow dragging the whole
    // shape. Passing draggable here keeps vertex-edit markers visible (calling
    // enableLayerDrag separately would hide them and only allow moving).
    (poly as any).pm.enable({
      allowSelfIntersection: false,
      draggable: true,
      snappable: false,
    });

    const commitShape = () => {
      const latlngs = (poly.getLatLngs()[0] as L.LatLng[]).map(
        (p) => [p.lat, p.lng] as [number, number]);
      if (latlngs.length >= 4) {
        const r = rectFromCorners(latlngs.slice(0, 4), b.lat);
        onChange(i, {
          lat: r.lat, lng: r.lng,
          width_m: Math.round(r.width_m),
          length_m: Math.round(r.length_m),
          angle_deg: Math.round(r.angle_deg),
        });
      }
      positionHandle();
    };
    poly.on('pm:markerdragend', commitShape);
    poly.on('pm:edit', commitShape);
    poly.on('pm:dragend', commitShape);

    // Draggable rotation handle placed just outside the polygon's north edge.
    const mLat = METERS_PER_DEG_LAT;
    const handle = L.marker([b.lat, b.lng], {
      draggable: true,
      zIndexOffset: 1000,
      icon: L.divIcon({
        className: 'rotate-handle',
        html: '<div style="width:18px;height:18px;border-radius:50%;background:#7c3aed;border:2px solid white;box-shadow:0 0 4px rgba(0,0,0,0.6);cursor:grab"></div>',
        iconSize: [18, 18], iconAnchor: [9, 9],
      }),
    }).addTo(map);
    layersRef.current.push(handle);

    // Keep the handle above the current polygon center as the shape changes.
    function positionHandle() {
      const c = poly.getBounds().getCenter();
      const halfLen = poly.getBounds().getNorth() - c.lat;
      handle.setLatLng([c.lat + halfLen + 12 / mLat, c.lng]);
    }
    positionHandle();

    handle.on('drag', () => {
      const c = poly.getBounds().getCenter();
      const hp = handle.getLatLng();
      const dLat = (hp.lat - c.lat);
      const dLng = (hp.lng - c.lng);
      // Target angle of the handle from center (0 = north, clockwise).
      const target = Math.atan2(dLng, dLat);
      const prev = (handle as any)._prevAngle ?? target;
      const delta = target - prev;
      (handle as any)._prevAngle = target;
      if (!delta) return;
      // Rotate every polygon vertex about the center by delta (live).
      const cosD = Math.cos(delta), sinD = Math.sin(delta);
      const mLatL = METERS_PER_DEG_LAT;
      const mLngL = METERS_PER_DEG_LAT * Math.cos((c.lat * Math.PI) / 180);
      const ring = (poly.getLatLngs()[0] as L.LatLng[]).map((p) => {
        const x = (p.lng - c.lng) * mLngL;
        const y = (p.lat - c.lat) * mLatL;
        const rx = x * cosD - y * sinD;
        const ry = x * sinD + y * cosD;
        return L.latLng(c.lat + ry / mLatL, c.lng + rx / mLngL);
      });
      poly.setLatLngs(ring);
    });
    handle.on('dragstart', () => { (handle as any)._prevAngle = undefined; });
    handle.on('dragend', () => {
      commitShape();
    });

    return () => {
      layersRef.current.forEach((l) => map.removeLayer(l));
      layersRef.current = [];
    };
    // Only rebuild when the selection changes, not on every geometry edit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIndex, map]);

  return null;
}

// Editable form shown in a building's popup: name, floors (=> height), width,
// length, and rotation. Commits changes to the parent, which recomputes the
// footprint polygon and persists.
function BuildingEditor({
  building, index, onApply, onDelete,
}: {
  building: DetectedFeature;
  index: number;
  onApply: (index: number, patch: Partial<DetectedFeature>) => void;
  onDelete: (index: number) => void;
}) {
  const [name, setName] = useState(building.name ?? '');
  const [floors, setFloors] = useState(building.floors ?? 1);
  const [width, setWidth] = useState(Math.round(building.width_m ?? 24));
  const [length, setLength] = useState(Math.round(building.length_m ?? 18));
  const [angle, setAngle] = useState(Math.round(building.angle_deg ?? 0));

  const apply = (patch: Partial<DetectedFeature>) => onApply(index, patch);

  return (
    <div className="text-xs min-w-[200px] text-slate-900">
      <strong className="text-sm">Building</strong>
      <div className="mt-2 space-y-2">
        <div>
          <label className="block text-slate-700 mb-0.5">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={() => apply({ name })}
            className="w-full border border-slate-300 rounded px-1.5 py-1"
            placeholder="e.g. Gym"
          />
        </div>
        <div className="flex items-center justify-between gap-2">
          <label className="text-slate-700">Floors</label>
          <div className="flex items-center gap-1">
            <button className="px-2 py-0.5 bg-slate-200 rounded font-bold"
              onClick={() => { const f = Math.max(1, floors - 1); setFloors(f); apply({ floors: f }); }}>-</button>
            <span className="w-8 text-center font-semibold">{floors}</span>
            <button className="px-2 py-0.5 bg-slate-200 rounded font-bold"
              onClick={() => { const f = floors + 1; setFloors(f); apply({ floors: f }); }}>+</button>
          </div>
        </div>
        <div className="text-slate-500 text-[10px] -mt-1">
          Height = {floors} x 3 m = <span className="font-semibold">{floors * 3} m</span>
        </div>
        <div>
          <label className="block text-slate-700 mb-0.5">Width: {width} m (E-W)</label>
          <input type="range" min={4} max={200} value={width}
            onChange={(e) => setWidth(parseInt(e.target.value))}
            onMouseUp={() => apply({ width_m: width })}
            onTouchEnd={() => apply({ width_m: width })}
            className="w-full accent-blue-600" />
        </div>
        <div>
          <label className="block text-slate-700 mb-0.5">Length: {length} m (N-S)</label>
          <input type="range" min={4} max={200} value={length}
            onChange={(e) => setLength(parseInt(e.target.value))}
            onMouseUp={() => apply({ length_m: length })}
            onTouchEnd={() => apply({ length_m: length })}
            className="w-full accent-blue-600" />
        </div>
        <div>
          <label className="block text-slate-700 mb-0.5">Rotation: {angle} deg</label>
          <input type="range" min={0} max={180} value={angle}
            onChange={(e) => setAngle(parseInt(e.target.value))}
            onMouseUp={() => apply({ angle_deg: angle })}
            onTouchEnd={() => apply({ angle_deg: angle })}
            className="w-full accent-blue-600" />
        </div>
        <button
          onClick={() => onDelete(index)}
          className="mt-1 w-full px-2 py-1 bg-red-500 text-white font-semibold rounded hover:bg-red-600 transition"
        >
          Delete (not a building)
        </button>
      </div>
    </div>
  );
}

export default function CampusMap({ heatmap, flora, buildings, campus, onTreeSelect }: CampusMapProps) {
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showDetected, setShowDetected] = useState(true);
  const [showBuildings, setShowBuildings] = useState(true);
  const [addingBuilding, setAddingBuilding] = useState(false);
  const [editingShape, setEditingShape] = useState(false);
  const [selectedBuildingIndex, setSelectedBuildingIndex] = useState<number | null>(null);
  const [detectedTrees, setDetectedTrees] = useState<DetectedFeature[]>([]);
  const [detectedBuildings, setDetectedBuildings] = useState<DetectedFeature[]>([]);
  const [detecting, setDetecting] = useState(true);

  const campusKey = campus?.key || 'gunn';

  // Map bounds from the selected campus (fall back to Gunn's bounds).
  const bounds: [[number, number], [number, number]] = campus
    ? [[campus.bounds.south, campus.bounds.west], [campus.bounds.north, campus.bounds.east]]
    : SATELLITE_BOUNDS;
  // Center the view on the image bounds (NOT the campus center, which can be
  // offset from the image and would leave a black strip on one side).
  const center: [number, number] = [
    (bounds[0][0] + bounds[1][0]) / 2,
    (bounds[0][1] + bounds[1][1]) / 2,
  ];

  const deleteTree = (index: number) => {
    const updated = detectedTrees.filter((_, i) => i !== index);
    setDetectedTrees(updated);
    // Save to backend
    fetch(`/api/detect/update?campus=${campusKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trees: updated }),
    }).catch(() => {});
  };

  const deleteBuilding = (index: number) => {
    const updated = detectedBuildings.filter((_, i) => i !== index);
    setDetectedBuildings(updated);
    // Persist the corrected building set to the cache the server serves.
    fetch(`/api/detect/update?campus=${campusKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ buildings: updated }),
    }).catch(() => {});
  };

  const persistBuildings = (updated: DetectedFeature[]) => {
    fetch(`/api/detect/update?campus=${campusKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ buildings: updated }),
    }).catch(() => {});
  };

  // Add a manually-placed building (default ~24 x 18 m footprint) at a point.
  const addBuilding = (lat: number, lng: number) => {
    const width_m = 24;
    const length_m = 18;
    const newBuilding: DetectedFeature = {
      lat, lng, type: 'building',
      width_m, length_m, angle_deg: 0,
      name: 'New building', floors: 1,
      polygon: rotatedRect(lat, lng, width_m, length_m, 0),
    };
    const updated = [...detectedBuildings, newBuilding];
    setDetectedBuildings(updated);
    persistBuildings(updated);
  };

  // Edit an existing building's name/floors/width/length/rotation; recompute
  // its footprint polygon and persist.
  const updateBuilding = (index: number, patch: Partial<DetectedFeature>) => {
    const updated = detectedBuildings.map((b, i) => {
      if (i !== index) return b;
      const merged = { ...b, ...patch };
      const w = merged.width_m ?? 24;
      const l = merged.length_m ?? 18;
      const ang = merged.angle_deg ?? 0;
      merged.polygon = rotatedRect(merged.lat, merged.lng, w, l, ang);
      return merged;
    });
    setDetectedBuildings(updated);
    persistBuildings(updated);
  };

  useEffect(() => {
    setDetecting(true);
    fetch(`/api/detect?campus=${campusKey}`)
      .then((r) => r.json())
      .then((data) => {
        setDetectedTrees(data.trees || []);
        setDetectedBuildings(data.buildings || []);
        setDetecting(false);
      })
      .catch(() => setDetecting(false));
  }, [campusKey]);

  return (
    <div className="w-full h-full relative" style={{ minHeight: '500px' }}>
      <MapContainer
        center={center}
        zoom={16}
        maxBounds={bounds}
        maxBoundsViscosity={1.0}
        style={{ width: '100%', height: '100%', background: '#0f172a' }}
        zoomControl={false}
        scrollWheelZoom={true}
        zoomSnap={0}
        zoomDelta={0.5}
        wheelPxPerZoomLevel={120}
        crs={L.CRS.EPSG3857}
      >
        {/* Clamp minimum zoom so the satellite image always fills the view */}
        <FitImageBounds bounds={bounds} />

        {/* Click-to-add-building when in add mode */}
        <AddBuildingHandler active={addingBuilding} onAdd={addBuilding} />

        {/* Use downloaded satellite image as background instead of tile API */}
        <ImageOverlay
          url={`/api/static/satellite.png?campus=${campusKey}`}
          bounds={bounds}
        />

        <ZoomControl position="bottomright" />

        {/* Heatmap overlay */}
        <HeatmapOverlay heatmap={heatmap} visible={showHeatmap} bounds={bounds} buildings={detectedBuildings} />

        {/* Detected building rooftops (SAM segmentation) */}
        {showBuildings && detectedBuildings.map((b, i) => (
          (editingShape && selectedBuildingIndex === i) ? null : (
          <Polygon
            key={`bldg-${i}`}
            positions={b.polygon as [number, number][]}
            pathOptions={{ color: '#1e3a8a', weight: 1.5, fillColor: '#3b82f6', fillOpacity: 0.35 }}
            eventHandlers={{
              click: () => { if (editingShape) setSelectedBuildingIndex(i); },
            }}
          >
            {!editingShape && (
            <Popup minWidth={220} maxWidth={260}>
              <BuildingEditor
                building={b}
                index={i}
                onApply={updateBuilding}
                onDelete={deleteBuilding}
              />
            </Popup>
            )}
          </Polygon>
          )
        ))}

        {/* Interactive shape editing for the selected building */}
        {editingShape && (
          <BuildingEditLayer
            selectedIndex={selectedBuildingIndex}
            building={selectedBuildingIndex !== null ? detectedBuildings[selectedBuildingIndex] : null}
            onChange={updateBuilding}
          />
        )}

        {/* Detected trees from satellite image recognition */}
        {showDetected && detectedTrees.map((tree, i) => {
          const species = SPECIES_INFO[tree.species_key || 'coast_live_oak'];
          const speciesColors: Record<string, string> = {
            valley_oak: '#dc2626', coast_live_oak: '#ef4444', redwood: '#166534',
            eucalyptus: '#6b7280', pine: '#064e3b', chinese_elm: '#ca8a04',
            sycamore: '#a16207', perennial_grass: '#84cc16', palm: '#0891b2',
          };
          const color = speciesColors[tree.species_key || ''] || '#22c55e';
          return (
            <Polygon
              key={`tree-${i}`}
              positions={tree.polygon as [number, number][]}
              pathOptions={{ color, weight: 2, fillColor: color, fillOpacity: 0.3 }}
            >
              <Popup>
                <div className="text-xs min-w-[160px]">
                  <strong className="text-sm">{species?.name || 'Tree'}</strong><br />
                  <em className="text-slate-500">{species?.scientific}</em><br />
                  <div className="mt-1 space-y-0.5">
                    <div>Family: <span className="font-medium">{species?.family}</span></div>
                    <div>Canopy radius: <span className="font-medium">{tree.radius_m}m</span></div>
                    <div>Allergen potency: <span className="font-medium">{species?.potency}/5</span></div>
                  </div>
                  <button
                    onClick={() => deleteTree(i)}
                    className="mt-2 w-full px-2 py-1 bg-red-500 text-white text-xs font-semibold rounded hover:bg-red-600 transition"
                  >
                    Delete (not a tree)
                  </button>
                </div>
              </Popup>
            </Polygon>
          );
        })}
      </MapContainer>

      {/* Controls */}
      <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2">
        <button
          onClick={() => setShowHeatmap(!showHeatmap)}
          className={`px-3 py-2 rounded-lg shadow-lg text-xs font-semibold transition-all ${
            showHeatmap ? 'bg-red-500 text-white' : 'bg-white text-slate-700 border border-slate-200'
          }`}
        >
          {showHeatmap ? 'Hide Heatmap' : 'Show Heatmap'}
        </button>
        <button
          onClick={() => setShowDetected(!showDetected)}
          className={`px-3 py-2 rounded-lg shadow-lg text-xs font-semibold transition-all ${
            showDetected ? 'bg-emerald-500 text-white' : 'bg-white text-slate-700 border border-slate-200'
          }`}
        >
          {showDetected ? 'Hide Detection' : 'Show Detection'}
        </button>
        <button
          onClick={() => setShowBuildings(!showBuildings)}
          className={`px-3 py-2 rounded-lg shadow-lg text-xs font-semibold transition-all ${
            showBuildings ? 'bg-blue-600 text-white' : 'bg-white text-slate-700 border border-slate-200'
          }`}
        >
          {showBuildings ? 'Hide Buildings' : 'Show Buildings'}
        </button>
        <button
          onClick={() => { setAddingBuilding(!addingBuilding); setShowBuildings(true); }}
          className={`px-3 py-2 rounded-lg shadow-lg text-xs font-semibold transition-all ${
            addingBuilding ? 'bg-amber-500 text-white' : 'bg-white text-slate-700 border border-slate-200'
          }`}
        >
          {addingBuilding ? 'Click map to add (done)' : 'Add Building'}
        </button>
        <button
          onClick={() => { setEditingShape(!editingShape); setShowBuildings(true); setSelectedBuildingIndex(null); }}
          className={`px-3 py-2 rounded-lg shadow-lg text-xs font-semibold transition-all ${
            editingShape ? 'bg-purple-600 text-white' : 'bg-white text-slate-700 border border-slate-200'
          }`}
        >
          {editingShape ? 'Editing shapes (done)' : 'Edit Shape'}
        </button>
      </div>

      {/* Add-building mode hint */}
      {addingBuilding && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-amber-500 text-white rounded-lg px-4 py-2 shadow-lg text-xs font-semibold">
          Click anywhere on the map to add a building. Click "Add Building" again to finish.
        </div>
      )}

      {/* Edit-shape mode hint */}
      {editingShape && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-purple-600 text-white rounded-lg px-4 py-2 shadow-lg text-xs font-semibold">
          {selectedBuildingIndex === null
            ? 'Click a building to select it, then drag its corners to resize or the purple dot to rotate.'
            : 'Drag corners to resize/reshape, drag the shape to move, or the purple dot to rotate. Click "Edit Shape" to finish.'}
        </div>
      )}

      {/* Status */}
      {detecting && (
        <div className="absolute top-4 left-4 z-[1000] bg-white/95 rounded-lg p-3 shadow-lg text-xs">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-emerald-600"></div>
            <span>Analyzing satellite imagery...</span>
          </div>
        </div>
      )}

      {/* Legend */}
      {!detecting && showDetected && (
        <div className="absolute top-4 left-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-lg text-xs">
          <p className="font-semibold text-slate-700 mb-2">Satellite Detection</p>
          <div className="flex items-center gap-2">
            <span className="w-4 h-3 border-2 border-green-500 bg-green-200/60 inline-block rounded-full"></span>
            <span>Tree Canopy ({detectedTrees.length} detected)</span>
          </div>
        </div>
      )}

      {/* Heatmap info */}
      {showHeatmap && heatmap && (
        <div className="absolute bottom-4 left-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-lg text-xs">
          <p className="font-semibold text-slate-700 mb-1">Pollen Concentration (Today)</p>
          <div className="flex items-center gap-1">
            <span className="text-green-600">Low</span>
            <div className="w-20 h-2 rounded-full" style={{
              background: 'linear-gradient(to right, #22c55e, #facc15, #f97316, #dc2626)'
            }} />
            <span className="text-red-700">High</span>
          </div>
          <p className="text-slate-500 mt-1">
            Current: {heatmap.max_concentration.toFixed(1)} grains/m³
          </p>
          <p className="text-slate-500">
            vs. Spring peak: {((heatmap as any).pct_of_peak || 0)}%
          </p>
          <p className="text-slate-400 text-[10px] mt-0.5">
            Scale fixed to 500 grains/m³ (spring max)
          </p>
        </div>
      )}
    </div>
  );
}
