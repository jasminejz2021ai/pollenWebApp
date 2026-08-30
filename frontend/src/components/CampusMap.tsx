import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import {
  MapContainer, ImageOverlay, Polygon, Popup,
  useMap, useMapEvents, ZoomControl, Tooltip,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
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

// Build a rectangle footprint (list of [lat,lng] corners) for a building from
// its center lat/lng and its width (E-W) and length (N-S) in meters.
function buildingCorners(
  lat: number, lng: number, width_m: number, length_m: number,
): [number, number][] {
  const dLat = (length_m / 2) / METERS_PER_DEG_LAT;
  const dLng = (width_m / 2) / (METERS_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180));
  return [
    [lat - dLat, lng - dLng],
    [lat - dLat, lng + dLng],
    [lat + dLat, lng + dLng],
    [lat + dLat, lng - dLng],
    [lat - dLat, lng - dLng],
  ];
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

function HeatmapOverlay({ heatmap, visible, bounds }: { heatmap: HeatmapResponse | null; visible: boolean; bounds: [[number, number], [number, number]] }) {
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

    const overlay = L.imageOverlay(canvas.toDataURL(), llBounds, { opacity: 0.7, interactive: false });
    overlay.addTo(map);
    overlayRef.current = overlay;
    return () => { if (overlayRef.current) { map.removeLayer(overlayRef.current); overlayRef.current = null; } };
  }, [heatmap, visible, map, bounds]);
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
    let didInitialFit = false;

    const applyFit = () => {
      // Container must have its real size before getBoundsZoom is meaningful.
      map.invalidateSize({ animate: false });
      // fillZoom (inside=true): image covers the whole viewport with no black
      // strips. fitZoom (inside=false): whole image visible.
      const fitZoom = map.getBoundsZoom(llBounds, false);
      const fillZoom = map.getBoundsZoom(llBounds, true);
      // Let the user zoom out to see the whole image, but no further.
      map.setMinZoom(fitZoom);
      if (!didInitialFit) {
        // Open covering the full width (no side strips).
        map.setView(llBounds.getCenter(), fillZoom, { animate: false });
        didInitialFit = true;
      }
    };

    // Run once the map is ready, then again on the next frame in case the
    // container was still sizing (a common cause of black strips on first load).
    map.whenReady(() => {
      applyFit();
      requestAnimationFrame(applyFit);
    });

    // On window/container resize, only re-fit to fill; do not fight the user's
    // current zoom (which would make the +/- buttons feel broken).
    const onResize = () => {
      map.invalidateSize({ animate: false });
      const fitZoom = map.getBoundsZoom(llBounds, false);
      const fillZoom = map.getBoundsZoom(llBounds, true);
      map.setMinZoom(fitZoom);
      if (map.getZoom() < fillZoom) {
        map.setView(llBounds.getCenter(), fillZoom, { animate: false });
      }
    };
    map.on('resize', onResize);
    return () => {
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

export default function CampusMap({ heatmap, flora, buildings, campus, onTreeSelect }: CampusMapProps) {
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showDetected, setShowDetected] = useState(true);
  const [showBuildings, setShowBuildings] = useState(true);
  const [addingBuilding, setAddingBuilding] = useState(false);
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
    const dLat = (length_m / 2) / METERS_PER_DEG_LAT;
    const dLng = (width_m / 2) / (METERS_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180));
    const polygon: [number, number][] = [
      [lat - dLat, lng - dLng],
      [lat - dLat, lng + dLng],
      [lat + dLat, lng + dLng],
      [lat + dLat, lng - dLng],
      [lat - dLat, lng - dLng],
    ];
    const newBuilding: DetectedFeature = {
      lat, lng, polygon, type: 'building',
      width_m, length_m,
    };
    const updated = [...detectedBuildings, newBuilding];
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
        <HeatmapOverlay heatmap={heatmap} visible={showHeatmap} bounds={bounds} />

        {/* Detected building rooftops (SAM segmentation) */}
        {showBuildings && detectedBuildings.map((b, i) => (
          <Polygon
            key={`bldg-${i}`}
            positions={b.polygon as [number, number][]}
            pathOptions={{ color: '#1e3a8a', weight: 1.5, fillColor: '#3b82f6', fillOpacity: 0.35 }}
          >
            <Popup>
              <div className="text-xs min-w-[150px]">
                <strong className="text-sm">Detected rooftop</strong><br />
                <div className="mt-1 space-y-0.5">
                  <div>Footprint: <span className="font-medium">{b.width_m} x {b.length_m ?? b.height_m} m</span></div>
                </div>
                <button
                  onClick={() => deleteBuilding(i)}
                  className="mt-2 w-full px-2 py-1 bg-red-500 text-white text-xs font-semibold rounded hover:bg-red-600 transition"
                >
                  Delete (not a building)
                </button>
              </div>
            </Popup>
          </Polygon>
        ))}

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
      </div>

      {/* Add-building mode hint */}
      {addingBuilding && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-amber-500 text-white rounded-lg px-4 py-2 shadow-lg text-xs font-semibold">
          Click anywhere on the map to add a building. Click "Add Building" again to finish.
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
