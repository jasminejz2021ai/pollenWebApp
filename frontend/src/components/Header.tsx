import type { WindData, ActiveSpecies, Campus } from '../utils/api';

interface HeaderProps {
  weather: WindData | null;
  activeSpecies: ActiveSpecies[];
  campuses: Campus[];
  campusKey: string;
  onCampusChange: (key: string) => void;
}

export default function Header({ weather, activeSpecies, campuses, campusKey, onCampusChange }: HeaderProps) {
  const windDirectionText = (deg: number) => {
    const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    return dirs[Math.round(deg / 45) % 8];
  };

  const activeCampus = campuses.find((c) => c.key === campusKey);

  return (
    <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shadow-sm">
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">
            Campus AeroAllergen Map
          </h1>
          <p className="text-xs text-slate-500">
            {activeCampus ? `${activeCampus.name} - ${activeCampus.subtitle}` : 'Loading campus...'}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {/* Campus selector */}
        {campuses.length > 0 && (
          <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5">
            {campuses.map((c) => (
              <button
                key={c.key}
                onClick={() => onCampusChange(c.key)}
                className={`px-3 py-1.5 rounded-md text-sm font-semibold transition-all ${
                  c.key === campusKey
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title={`${c.name} - ${c.subtitle}`}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}

        {activeSpecies.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-red-500 risk-pulse"></span>
            <span className="text-sm text-slate-700">
              {activeSpecies.length} active pollen source{activeSpecies.length > 1 ? 's' : ''}
            </span>
          </div>
        )}

        {weather && (
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <div className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
              <span
                style={{ transform: `rotate(${weather.direction}deg)` }}
                className="inline-block"
              >
                ↑
              </span>
              <span>{weather.speed.toFixed(1)} m/s {windDirectionText(weather.direction)}</span>
            </div>
            <div>{weather.temperature}°C</div>
            <div className="text-xs bg-slate-100 px-2 py-0.5 rounded">
              Stability: {weather.stability_class}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
