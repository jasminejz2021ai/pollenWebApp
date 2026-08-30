const API_BASE = (import.meta as any).env?.VITE_API_URL || '/api';

export interface Campus {
  key: string;
  name: string;
  subtitle: string;
  center_lat: number;
  center_lon: number;
  bounds: { north: number; south: number; east: number; west: number };
  boundary: Array<{ lat: number; lng: number }>;
}

export interface TestParams {
  day?: number;        // Julian day of year (1-365)
  wind_speed?: number; // m/s
  wind_dir?: number;   // degrees from North
  stability?: string;  // Pasquill-Gifford A-F
}

function q(campus?: string, height?: number, test?: TestParams): string {
  const params: string[] = [];
  if (campus) params.push(`campus=${encodeURIComponent(campus)}`);
  if (height != null) params.push(`height=${encodeURIComponent(height)}`);
  if (test) {
    if (test.day != null) params.push(`day=${test.day}`);
    if (test.wind_speed != null) params.push(`wind_speed=${test.wind_speed}`);
    if (test.wind_dir != null) params.push(`wind_dir=${test.wind_dir}`);
    if (test.stability) params.push(`stability=${test.stability}`);
  }
  return params.length ? `?${params.join('&')}` : '';
}

export interface WindData {
  speed: number;
  direction: number;
  u: number;
  v: number;
  temperature: number;
  humidity: number;
  stability_class: string;
  timestamp: string;
  source: string;
}

export interface FloraItem {
  x: number;
  y: number;
  lat: number;
  lng: number;
  species_key: string;
  common_name: string;
  scientific_name: string;
  family: string;
  potency_weight: number;
  is_active: boolean;
  symptoms: string;
}

export interface ActiveSpecies {
  species_key: string;
  common_name: string;
  scientific_name: string;
  family: string;
  potency_weight: number;
  gamma: number;
  effective_emission: number;
  symptoms: string;
}

export interface HeatmapPoint {
  lat: number;
  lng: number;
  weight: number;
}

export interface HeatmapResponse {
  points: HeatmapPoint[];
  max_concentration: number;
  wind: WindData;
  active_species: ActiveSpecies[];
}

export interface Building {
  building_id: string;
  name: string;
  height: number;
  width: number;
  length: number;
  local_x: number;
  local_y: number;
  lat: number;
  lng: number;
}

export interface ClinicalLevel {
  level: string;
  severity: string;
  symptoms: string;
  recommendation: string;
  color: string;
}

export interface PollenForecast {
  date: string;
  tree_upi: number;
  grass_upi: number;
  weed_upi: number;
  dominant_species: string | null;
  clinical: ClinicalLevel;
}

export interface PathExposure {
  total_dose: number;
  max_concentration: number;
  risk_level: string;
  path_length_m: number;
  transit_time_s: number;
  segment_doses: Array<{
    from: [number, number];
    to: [number, number];
    concentration: number;
    dose: number;
    duration_s: number;
  }>;
}

export interface Advisory {
  clinical_level: ClinicalLevel;
  regional_upi: { tree_upi: number; grass_upi: number; weed_upi: number };
  active_species: ActiveSpecies[];
  wind: WindData;
  path_advisories: Array<{
    path_name: string;
    risk_level: string;
    total_dose: number;
    max_concentration: number;
  }>;
  advisory_message: string;
  timestamp: string;
}

export async function fetchCampuses(): Promise<{ campuses: Campus[]; default: string }> {
  const res = await fetch(`${API_BASE}/campuses`);
  return res.json();
}

export async function fetchHeatmap(campus?: string, height?: number, test?: TestParams): Promise<HeatmapResponse> {
  const res = await fetch(`${API_BASE}/heatmap${q(campus, height, test)}`);
  return res.json();
}

export async function fetchFlora(campus?: string): Promise<{ flora: FloraItem[]; active_species: ActiveSpecies[] }> {
  const res = await fetch(`${API_BASE}/flora${q(campus)}`);
  return res.json();
}

export async function fetchBuildings(campus?: string): Promise<{ buildings: Building[] }> {
  const res = await fetch(`${API_BASE}/buildings${q(campus)}`);
  return res.json();
}

export async function fetchWeather(campus?: string, test?: TestParams): Promise<WindData> {
  const res = await fetch(`${API_BASE}/weather${q(campus, undefined, test)}`);
  return res.json();
}

export async function fetchPollenForecast(campus?: string): Promise<{ forecasts: PollenForecast[] }> {
  const res = await fetch(`${API_BASE}/pollen-forecast${q(campus)}`);
  return res.json();
}

export async function fetchPathExposure(path: [number, number][], campus?: string): Promise<PathExposure> {
  const res = await fetch(`${API_BASE}/path-exposure${q(campus)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  return res.json();
}

export async function fetchOptimalRoute(
  start: [number, number],
  end: [number, number],
  campus?: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/optimal-route${q(campus)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start, end }),
  });
  return res.json();
}

export async function fetchAdvisory(campus?: string, height?: number, test?: TestParams): Promise<Advisory> {
  const res = await fetch(`${API_BASE}/advisory${q(campus, height, test)}`);
  return res.json();
}
