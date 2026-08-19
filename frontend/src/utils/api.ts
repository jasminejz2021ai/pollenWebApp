const API_BASE = (import.meta as any).env?.VITE_API_URL || '/api';

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

export async function fetchHeatmap(): Promise<HeatmapResponse> {
  const res = await fetch(`${API_BASE}/heatmap`);
  return res.json();
}

export async function fetchFlora(): Promise<{ flora: FloraItem[]; active_species: ActiveSpecies[] }> {
  const res = await fetch(`${API_BASE}/flora`);
  return res.json();
}

export async function fetchBuildings(): Promise<{ buildings: Building[] }> {
  const res = await fetch(`${API_BASE}/buildings`);
  return res.json();
}

export async function fetchWeather(): Promise<WindData> {
  const res = await fetch(`${API_BASE}/weather`);
  return res.json();
}

export async function fetchPollenForecast(): Promise<{ forecasts: PollenForecast[] }> {
  const res = await fetch(`${API_BASE}/pollen-forecast`);
  return res.json();
}

export async function fetchPathExposure(path: [number, number][]): Promise<PathExposure> {
  const res = await fetch(`${API_BASE}/path-exposure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  return res.json();
}

export async function fetchOptimalRoute(
  start: [number, number],
  end: [number, number]
): Promise<any> {
  const res = await fetch(`${API_BASE}/optimal-route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start, end }),
  });
  return res.json();
}

export async function fetchAdvisory(): Promise<Advisory> {
  const res = await fetch(`${API_BASE}/advisory`);
  return res.json();
}
