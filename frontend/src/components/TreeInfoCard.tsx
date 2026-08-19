import type { FloraItem, ActiveSpecies, WindData } from '../utils/api';

interface TreeInfoCardProps {
  tree: FloraItem;
  activeSpecies: ActiveSpecies[];
  weather: WindData | null;
  onClose: () => void;
}

export default function TreeInfoCard({ tree, activeSpecies, weather, onClose }: TreeInfoCardProps) {
  const activeInfo = activeSpecies.find((s) => s.species_key === tree.species_key);
  const potencyBars = Math.round(tree.potency_weight);

  const riskLevel = tree.is_active
    ? tree.potency_weight >= 4 ? 'high' : 'moderate'
    : 'inactive';

  const riskStyles = {
    high: 'text-red-600 bg-red-50',
    moderate: 'text-amber-600 bg-amber-50',
    inactive: 'text-slate-500 bg-slate-100',
  };

  const riskLabels = {
    high: 'Active Pollination Peak',
    moderate: 'Moderate Emission',
    inactive: 'Dormant / Off-Season',
  };

  return (
    <div className="max-w-sm bg-white rounded-xl shadow-xl overflow-hidden border border-slate-200 animate-in">
      <div className="p-5">
        <div className="flex justify-between items-center">
          <span className={`uppercase tracking-wide text-xs font-semibold px-2.5 py-1 rounded-full ${riskStyles[riskLevel]}`}>
            {riskLabels[riskLevel]}
          </span>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <h2 className="mt-2 text-lg font-bold text-slate-900">
          {tree.common_name}{' '}
          <span className="text-sm font-normal italic text-slate-500">
            ({tree.scientific_name})
          </span>
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">Family: {tree.family}</p>

        <div className="grid grid-cols-2 gap-3 my-4 bg-slate-50 p-3 rounded-lg text-sm">
          <div>
            <p className="text-slate-500 font-medium text-xs">Emission Rate</p>
            <p className="text-base font-bold text-slate-800">
              {activeInfo ? `${activeInfo.effective_emission.toFixed(0)} g/s` : 'Dormant'}
            </p>
          </div>
          <div>
            <p className="text-slate-500 font-medium text-xs">Potency Index</p>
            <div className="flex items-center gap-1 mt-0.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`w-3 h-3 rounded-sm ${i < potencyBars ? 'bg-red-500' : 'bg-slate-200'}`}
                />
              ))}
              <span className="text-xs text-slate-600 ml-1">{tree.potency_weight}/5</span>
            </div>
          </div>
          {activeInfo && (
            <>
              <div>
                <p className="text-slate-500 font-medium text-xs">Bloom Intensity</p>
                <p className="text-base font-bold text-slate-800">{(activeInfo.gamma * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-slate-500 font-medium text-xs">Wind Exposure</p>
                <p className="text-base font-bold text-amber-600">
                  {weather && weather.speed > 3 ? 'High Dispersal' : 'Moderate'}
                </p>
              </div>
            </>
          )}
        </div>

        {tree.symptoms && (
          <div className="mt-3 p-3 bg-rose-50 border-l-4 border-rose-500 rounded-r-md">
            <p className="text-xs font-bold uppercase text-rose-700 tracking-wider">
              Clinical Symptoms
            </p>
            <p className="text-sm text-rose-900 mt-1 leading-relaxed">{tree.symptoms}</p>
          </div>
        )}

        {weather && tree.is_active && (
          <div className="mt-3 p-3 bg-blue-50 border-l-4 border-blue-400 rounded-r-md">
            <p className="text-xs font-bold uppercase text-blue-700 tracking-wider">
              Current Dispersion
            </p>
            <p className="text-sm text-blue-900 mt-1">
              Wind from {windDirText(weather.direction)} at {weather.speed.toFixed(1)} m/s is
              dispersing pollen {weather.speed > 3 ? 'rapidly' : 'moderately'} across campus.
              {weather.speed > 4 && ' Consider wearing N95 mask in proximity.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function windDirText(deg: number): string {
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return dirs[Math.round(deg / 45) % 8];
}
