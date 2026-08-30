import { useState, useEffect, useCallback } from 'react';
import {
  fetchHeatmap, fetchFlora, fetchBuildings, fetchWeather,
  fetchPollenForecast, fetchAdvisory,
  HeatmapResponse, FloraItem, ActiveSpecies, Building, WindData,
  PollenForecast, Advisory, TestParams,
} from '../utils/api';

export function usePollenData(campus: string, height: number = 1.5, test?: TestParams) {
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [flora, setFlora] = useState<FloraItem[]>([]);
  const [activeSpecies, setActiveSpecies] = useState<ActiveSpecies[]>([]);
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [weather, setWeather] = useState<WindData | null>(null);
  const [forecast, setForecast] = useState<PollenForecast[]>([]);
  const [advisory, setAdvisory] = useState<Advisory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    try {
      setLoading(true);
      const [heatmapData, floraData, buildingData, weatherData, forecastData, advisoryData] =
        await Promise.all([
          fetchHeatmap(campus, height, test),
          fetchFlora(campus),
          fetchBuildings(campus),
          fetchWeather(campus, test),
          fetchPollenForecast(campus),
          fetchAdvisory(campus, height, test),
        ]);

      setHeatmap(heatmapData);
      setFlora(floraData.flora);
      setActiveSpecies(floraData.active_species);
      setBuildings(buildingData.buildings);
      setWeather(weatherData);
      setForecast(forecastData.forecasts);
      setAdvisory(advisoryData);
      setError(null);
    } catch (err) {
      setError('Failed to load pollen data. Ensure backend is running.');
    } finally {
      setLoading(false);
    }
  }, [campus, height, JSON.stringify(test)]);

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 300000); // refresh every 5 min
    return () => clearInterval(interval);
  }, [refreshData]);

  return {
    heatmap, flora, activeSpecies, buildings, weather, forecast, advisory,
    loading, error, refreshData,
  };
}
