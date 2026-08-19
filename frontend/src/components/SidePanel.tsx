import type { PollenForecast, Advisory, ActiveSpecies, WindData } from '../utils/api';

interface SidePanelProps {
  forecast: PollenForecast[];
  advisory: Advisory | null;
  activeSpecies: ActiveSpecies[];
  weather: WindData | null;
}

export default function SidePanel({ forecast, advisory, activeSpecies, weather }: SidePanelProps) {
  return (
    <aside className="w-80 bg-white border-l border-slate-200 overflow-y-auto flex-shrink-0">
      <div className="p-4 space-y-5">
        {/* Active Species Section */}
        <section>
          <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
            Active Pollen Sources
          </h3>
          {activeSpecies.length === 0 ? (
            <p className="text-sm text-slate-500 italic">No active sources today</p>
          ) : (
            <div className="space-y-2">
              {activeSpecies.map((species) => (
                <div
                  key={species.species_key}
                  className="bg-slate-50 rounded-lg p-3 border border-slate-100"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-semibold text-sm text-slate-800">
                        {species.common_name}
                      </p>
                      <p className="text-xs text-slate-500 italic">
                        {species.scientific_name}
                      </p>
                    </div>
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-red-100 text-red-700">
                      {species.potency_weight}/5
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-xs text-slate-600">
                    <span>Bloom: {(species.gamma * 100).toFixed(0)}%</span>
                    <span>Emission: {species.effective_emission.toFixed(0)} g/s</span>
                  </div>
                  <div className="mt-1.5 w-full bg-slate-200 rounded-full h-1.5">
                    <div
                      className="bg-red-500 h-1.5 rounded-full transition-all"
                      style={{ width: `${species.gamma * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 5-Day Forecast Section */}
        <section>
          <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
            Regional Pollen Forecast
          </h3>
          <div className="space-y-2">
            {forecast.slice(0, 5).map((day, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50"
              >
                <div>
                  <p className="text-xs font-medium text-slate-700">{day.date}</p>
                  <p className="text-xs text-slate-500">{day.dominant_species || 'Mixed'}</p>
                </div>
                <div className="flex gap-1.5">
                  <UPIBadge label="T" value={day.tree_upi} />
                  <UPIBadge label="G" value={day.grass_upi} />
                  <UPIBadge label="W" value={day.weed_upi} />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Path Risk Section */}
        {advisory && advisory.path_advisories.length > 0 && (
          <section>
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
              Route Risk Assessment
            </h3>
            <div className="space-y-2">
              {advisory.path_advisories.map((path, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100"
                >
                  <span className="text-xs text-slate-700 font-medium">{path.path_name}</span>
                  <RiskBadge level={path.risk_level} />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Wind Info */}
        {weather && (
          <section className="bg-blue-50 rounded-lg p-3 border border-blue-100">
            <h3 className="text-xs font-bold text-blue-800 uppercase tracking-wider mb-2">
              Wind Conditions
            </h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-blue-600">Speed:</span>{' '}
                <span className="font-semibold">{weather.speed.toFixed(1)} m/s</span>
              </div>
              <div>
                <span className="text-blue-600">Direction:</span>{' '}
                <span className="font-semibold">{weather.direction}°</span>
              </div>
              <div>
                <span className="text-blue-600">Stability:</span>{' '}
                <span className="font-semibold">Class {weather.stability_class}</span>
              </div>
              <div>
                <span className="text-blue-600">Source:</span>{' '}
                <span className="font-semibold capitalize">{weather.source}</span>
              </div>
            </div>
          </section>
        )}

        {/* Clinical Guide */}
        <section>
          <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
            Clinical Reference
          </h3>
          <div className="space-y-1.5 text-xs">
            <ClinicalRow color="#22c55e" label="UPI 0-1" desc="Safe. No measures needed." />
            <ClinicalRow color="#facc15" label="UPI 2-3" desc="Antihistamines recommended. Avoid tree zones." />
            <ClinicalRow color="#ef4444" label="UPI 4-5" desc="N95 mask required. Move PE indoors." />
          </div>
        </section>
      </div>
    </aside>
  );
}

function UPIBadge({ label, value }: { label: string; value: number }) {
  const colors = ['bg-green-100 text-green-700', 'bg-green-100 text-green-700', 'bg-yellow-100 text-yellow-700', 'bg-orange-100 text-orange-700', 'bg-red-100 text-red-700', 'bg-red-200 text-red-800'];
  return (
    <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${colors[value] || colors[0]}`}>
      {label}:{value}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    low: 'bg-green-100 text-green-700',
    moderate: 'bg-yellow-100 text-yellow-700',
    high: 'bg-orange-100 text-orange-700',
    very_high: 'bg-red-100 text-red-700',
  };
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded ${styles[level] || styles.low}`}>
      {level.replace('_', ' ')}
    </span>
  );
}

function ClinicalRow({ color, label, desc }: { color: string; label: string; desc: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
      <span className="font-semibold text-slate-700 w-14">{label}</span>
      <span className="text-slate-600">{desc}</span>
    </div>
  );
}
