import { useState } from 'react';
import type { TestParams } from '../utils/api';

interface TestModePanelProps {
  enabled: boolean;
  params: TestParams;
  onToggle: (enabled: boolean) => void;
  onChange: (params: TestParams) => void;
}

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

// Approximate day-of-year for the 15th of each month.
const MONTH_DAY = [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349];

const STABILITY = [
  { v: 'A', label: 'A - Very unstable' },
  { v: 'B', label: 'B - Unstable' },
  { v: 'C', label: 'C - Slightly unstable' },
  { v: 'D', label: 'D - Neutral' },
  { v: 'E', label: 'E - Slightly stable' },
  { v: 'F', label: 'F - Stable' },
];

const CARDINALS = [
  { v: 0, label: 'N' }, { v: 45, label: 'NE' }, { v: 90, label: 'E' },
  { v: 135, label: 'SE' }, { v: 180, label: 'S' }, { v: 225, label: 'SW' },
  { v: 270, label: 'W' }, { v: 315, label: 'NW' },
];

export default function TestModePanel({ enabled, params, onToggle, onChange }: TestModePanelProps) {
  const [open, setOpen] = useState(false);

  // Adjusting any input applies the change and turns test mode on so the map
  // updates immediately (no separate "enable" step required).
  const set = (patch: Partial<TestParams>) => {
    onChange({ ...params, ...patch });
    if (!enabled) onToggle(true);
  };

  const day = params.day ?? 105;
  const monthIdx = MONTH_DAY.reduce(
    (best, d, i) => (Math.abs(d - day) < Math.abs(MONTH_DAY[best] - day) ? i : best), 0);

  return (
    <div className="absolute bottom-4 left-4 z-[1000]">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className={`px-3 py-2 rounded-lg shadow-lg text-xs font-semibold transition-all ${
            enabled ? 'bg-purple-600 text-white' : 'bg-white text-slate-700 border border-slate-200'
          }`}
        >
          {enabled ? 'Test Mode: ON' : 'Test Mode'}
        </button>
      ) : (
        <div className="bg-white/97 backdrop-blur-sm rounded-xl p-4 shadow-xl border border-slate-200 w-72 text-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-slate-800 text-sm">Test / Simulation Mode</span>
            <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-700">x</button>
          </div>

          <div className="flex items-center justify-between mb-3">
            <span className={`font-semibold ${enabled ? 'text-purple-700' : 'text-slate-800'}`}>
              {enabled ? 'Simulating custom conditions' : 'Using live weather'}
            </span>
            <button
              onClick={() => onToggle(!enabled)}
              className={`px-2 py-1 rounded-md font-semibold transition-all ${
                enabled ? 'bg-slate-200 text-slate-700' : 'bg-purple-600 text-white'
              }`}
            >
              {enabled ? 'Use live weather' : 'Turn on'}
            </button>
          </div>

          <div>
            {/* Date / month */}
            <div className="mb-3">
              <label className="block text-slate-900 mb-1">Month (season)</label>
              <select
                value={monthIdx}
                onChange={(e) => set({ day: MONTH_DAY[parseInt(e.target.value)] })}
                className="w-full border border-slate-200 rounded-md px-2 py-1"
              >
                {MONTHS.map((m, i) => <option key={m} value={i}>{m}</option>)}
              </select>
            </div>

            {/* Wind speed */}
            <div className="mb-3">
              <label className="block text-slate-900 mb-1">
                Wind speed: <span className="font-semibold text-slate-900">{params.wind_speed ?? 3.5} m/s</span>
              </label>
              <input
                type="range" min={0.5} max={15} step={0.5}
                value={params.wind_speed ?? 3.5}
                onChange={(e) => set({ wind_speed: parseFloat(e.target.value) })}
                className="w-full accent-purple-600"
              />
            </div>

            {/* Wind direction */}
            <div className="mb-3">
              <label className="block text-slate-900 mb-1">Wind from</label>
              <div className="grid grid-cols-4 gap-1">
                {CARDINALS.map((c) => (
                  <button
                    key={c.v}
                    onClick={() => set({ wind_dir: c.v })}
                    className={`py-1 rounded-md font-semibold transition-all ${
                      (params.wind_dir ?? 240) === c.v
                        ? 'bg-purple-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Stability */}
            <div className="mb-1">
              <label className="block text-slate-900 mb-1">Atmospheric stability</label>
              <select
                value={params.stability ?? 'D'}
                onChange={(e) => set({ stability: e.target.value })}
                className="w-full border border-slate-200 rounded-md px-2 py-1"
              >
                {STABILITY.map((s) => <option key={s.v} value={s.v}>{s.label}</option>)}
              </select>
            </div>

            <p className="text-[10px] text-slate-600 mt-2">
              Changing any value simulates that condition. Temperature and humidity
              are shown for context but do not affect the modeled concentration.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
