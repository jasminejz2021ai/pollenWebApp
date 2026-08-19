import type { Advisory } from '../utils/api';

interface AdvisoryBannerProps {
  advisory: Advisory;
}

export default function AdvisoryBanner({ advisory }: AdvisoryBannerProps) {
  if (!advisory.advisory_message) return null;

  const riskColor = {
    low: 'bg-green-50 border-green-400 text-green-800',
    moderate: 'bg-yellow-50 border-yellow-400 text-yellow-800',
    high: 'bg-orange-50 border-orange-400 text-orange-800',
    very_high: 'bg-red-50 border-red-500 text-red-800',
  };

  const highRiskPaths = advisory.path_advisories.filter(
    (p) => p.risk_level === 'high' || p.risk_level === 'very_high'
  );
  const worstRisk = highRiskPaths.length > 0 ? highRiskPaths[0].risk_level : 'moderate';
  const colorClass = riskColor[worstRisk as keyof typeof riskColor] || riskColor.moderate;

  return (
    <div className={`px-6 py-3 border-l-4 ${colorClass} flex items-start gap-3`}>
      <div className="flex-shrink-0 mt-0.5">
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
      </div>
      <div className="flex-1">
        <p className="text-xs font-bold uppercase tracking-wider mb-1">
          Clinical Morning Advisory
        </p>
        <p className="text-sm leading-relaxed">{advisory.advisory_message}</p>
      </div>
      <div className="flex-shrink-0 text-xs opacity-75">
        {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </div>
    </div>
  );
}
