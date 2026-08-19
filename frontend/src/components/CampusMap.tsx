import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import {
  MapContainer, ImageOverlay, Polygon, Popup,
  useMap, ZoomControl, Tooltip,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { HeatmapResponse, FloraItem, Building } from '../utils/api';

interface CampusMapProps {
  heatmap: HeatmapResponse | null;
  flora: FloraItem[];
  buildings: Building[];
  onTreeSelect: (tree: FloraItem) => void;
}

const CAMPUS_CENTER: [number, number] = [37.4012, -122.1340];

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
  species_key?: string;
}

const SPECIES_INFO: Record<string, { name: string; scientific: string; family: string; potency: number }> = {
  valley_oak: { name: "Valley Oak", scientific: "Quercus lobata", family: "Fagaceae", potency: 4.5 },
  coast_live_oak: { name: "Coast Live Oak", scientific: "Quercus agrifolia", family: "Fagaceae", potency: 4.0 },
  redwood: { name: "Coast Redwood", scientific: "Sequoia sempervirens", family: "Cupressaceae", potency: 2.5 },
  eucalyptus: { name: "Eucalyptus", scientific: "Eucalyptus spp.", family: "Myrtaceae", potency: 2.0 },
  pine: { name: "Pine", scientific: "Pinus spp.", family: "Pinaceae", potency: 2.0 },
  chinese_elm: { name: "Chinese Elm", scientific: "Ulmus parvifolia", family: "Ulmaceae", potency: 3.0 },
  sycamore: { name: "Western Sycamore", scientific: "Platanus racemosa", family: "Platanaceae", potency: 3.5 },
  perennial_grass: { name: "Turf Grass", scientific: "Poaceae spp.", family: "Poaceae", potency: 4.0 },
};

function HeatmapOverlay({ heatmap, visible }: { heatmap: HeatmapResponse | null; visible: boolean }) {
  const map = useMap();
  const overlayRef = useRef<L.ImageOverlay | null>(null);

  useEffect(() => {
    if (overlayRef.current) { map.removeLayer(overlayRef.current); overlayRef.current = null; }
    if (!visible || !heatmap || !heatmap.points.length) return;

    const bounds = L.latLngBounds([37.3988, -122.1372], [37.4038, -122.1300]);
    const canvas = document.createElement('canvas');
    canvas.width = 500; canvas.height = 500;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const south = bounds.getSouth(), north = bounds.getNorth();
    const west = bounds.getWest(), east = bounds.getEast();

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

    const overlay = L.imageOverlay(canvas.toDataURL(), bounds, { opacity: 0.7, interactive: false });
    overlay.addTo(map);
    overlayRef.current = overlay;
    return () => { if (overlayRef.current) { map.removeLayer(overlayRef.current); overlayRef.current = null; } };
  }, [heatmap, visible, map]);
  return null;
}

export default function CampusMap({ heatmap, flora, buildings, onTreeSelect }: CampusMapProps) {
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showDetected, setShowDetected] = useState(true);
  const [detectedTrees, setDetectedTrees] = useState<DetectedFeature[]>([]);
  const [detectedBuildings, setDetectedBuildings] = useState<DetectedFeature[]>([]);
  const [detecting, setDetecting] = useState(true);

  const deleteTree = (index: number) => {
    const updated = detectedTrees.filter((_, i) => i !== index);
    setDetectedTrees(updated);
    // Save to backend
    fetch('/api/detect/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trees: updated }),
    }).catch(() => {});
  };

  useEffect(() => {
    fetch('/api/detect')
      .then((r) => r.json())
      .then((data) => {
        setDetectedTrees(data.trees || []);
        setDetectedBuildings(data.buildings || []);
        setDetecting(false);
      })
      .catch(() => setDetecting(false));
  }, []);

  return (
    <div className="w-full h-full relative" style={{ minHeight: '500px' }}>
      <MapContainer
        center={[37.4015, -122.1338]}
        zoom={18}
        maxBounds={[[37.3980, -122.1380], [37.4046, -122.1292]]}
        maxBoundsViscosity={1.0}
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
        scrollWheelZoom={true}
        crs={L.CRS.EPSG3857}
      >
        {/* Use downloaded satellite image as background instead of tile API */}
        <ImageOverlay
          url="/api/static/satellite.png"
          bounds={[[37.3988, -122.1372], [37.4038, -122.1300]]}
        />

        <ZoomControl position="bottomright" />

        {/* Heatmap overlay */}
        <HeatmapOverlay heatmap={heatmap} visible={showHeatmap} />

        {/* Detected trees from satellite image recognition */}
        {showDetected && detectedTrees.map((tree, i) => {
          const species = SPECIES_INFO[tree.species_key || 'coast_live_oak'];
          const speciesColors: Record<string, string> = {
            valley_oak: '#dc2626', coast_live_oak: '#ef4444', redwood: '#166534',
            eucalyptus: '#6b7280', pine: '#064e3b', chinese_elm: '#ca8a04',
            sycamore: '#a16207', perennial_grass: '#84cc16',
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
      </div>

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
