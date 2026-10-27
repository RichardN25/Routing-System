import React from 'react';
import {
  Clock,
  Navigation,
  Calendar,
  AlertOctagon,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import {
  RISK_CONFIG,
  formatDuration,
  formatETA,
  formatDistance,
} from '../../utils/riskColors';

export const RouteCard = ({
  route,
  isSelected = false,
  onSelect,
  routeIndex = 1,
}) => {
  if (!route) return null;

  const {
    id,
    name,
    is_recommended = false,
    recommendation_reason = '',
    has_no_travel_warning = false,
    summary = {},
  } = route;

  const totalDistance = summary.total_distance_miles || 0;
  const noTravelMiles = summary.no_travel_miles || 0;
  const severeMiles = summary.severe_miles || 0;
  const highMiles = summary.high_miles || 0;
  const moderateMiles = summary.moderate_miles || 0;
  const lowMiles = summary.low_miles || 0;
  const avgRisk = summary.average_risk_score !== undefined ? Number(summary.average_risk_score).toFixed(2) : '0.00';
  const sampleInterval = summary.sample_interval_miles;

  const hasNoTravel = has_no_travel_warning || noTravelMiles > 0;

  // Compute percentages for the stacked bar
  const getPercentage = (miles) => {
    if (!totalDistance || totalDistance <= 0) return 0;
    return Math.max(0, Math.min(100, (miles / totalDistance) * 100));
  };

  const pctNoTravel = getPercentage(noTravelMiles);
  const pctSevere = getPercentage(severeMiles);
  const pctHigh = getPercentage(highMiles);
  const pctModerate = getPercentage(moderateMiles);
  const pctLow = getPercentage(lowMiles);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect?.(id);
    }
  };

  const formatRouteTitle = (rawName, idx) => {
    if (!rawName) return `Route Option ${idx}`;
    const trimmed = rawName.trim();
    if (/^\d+$/.test(trimmed)) {
      return `via Route ${trimmed}`;
    }
    if (!trimmed.toLowerCase().startsWith('via') && !trimmed.toLowerCase().startsWith('route')) {
      return `via ${trimmed}`;
    }
    return trimmed;
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(id)}
      onKeyDown={handleKeyDown}
      className={`rounded-xl p-4 transition-all duration-200 border text-left cursor-pointer focus:outline-none relative overflow-hidden ${
        isSelected
          ? is_recommended
            ? 'bg-[#141414] border-[#f9564f] ring-2 ring-[#f9564f]/30 shadow-lg shadow-[#141414]/50'
            : hasNoTravel
            ? 'bg-[#141414] border-fuchsia-600 ring-2 ring-fuchsia-600/30 shadow-lg shadow-fuchsia-950/30'
            : 'bg-[#141414] border-[#f9564f] ring-2 ring-[#f9564f]/30 shadow-lg shadow-[#141414]/50'
          : 'bg-[#141414] border-neutral-600 hover:border-[#f9564f]/60'
      }`}
    >
      {/* Top Header Row */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold ${
                is_recommended
                  ? 'bg-[#f9564f] text-black border border-[#f9564f]'
                  : 'bg-neutral-600 text-white border border-neutral-500'
              }`}
            >
              {routeIndex}
            </span>
            <h3 className="font-semibold text-slate-100 text-sm tracking-tight truncate max-w-[210px]">
              {formatRouteTitle(name, routeIndex)}
            </h3>
          </div>
          {sampleInterval && (
            <span className="text-[10px] text-slate-400 pl-7">
              {sampleInterval} mi dynamic sampling
            </span>
          )}
        </div>

        {/* Selected Indicator Pill */}
        {isSelected && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#f9564f]/20 text-[#f9564f] border border-[#f9564f]/40">
            <CheckCircle2 className="w-3 h-3 text-[#f9564f]" />
            Selected
          </span>
        )}
      </div>

      {/* Recommended Route Badge */}
      {is_recommended && (
        <div className="mb-2.5 p-2 rounded-lg bg-[#f9564f]/15 border border-[#f9564f]/30 text-slate-200 space-y-0.5">
          <div className="flex items-center gap-1.5 text-xs font-bold tracking-wide text-[#f9564f]">
            <span>★ Recommended Route</span>
          </div>
          {recommendation_reason && (
            <p className="text-[11px] text-slate-300 leading-tight">
              {recommendation_reason}
            </p>
          )}
        </div>
      )}

      {/* No Travel Warning Banner */}
      {hasNoTravel && (
        <div className="mb-2.5 p-2 rounded-lg bg-fuchsia-950/90 border border-fuchsia-500 text-fuchsia-200 flex items-start gap-2 shadow-sm">
          <AlertOctagon className="w-4 h-4 text-fuchsia-400 mt-0.5 shrink-0" />
          <div className="text-[11px] leading-tight">
            <strong className="font-bold text-fuchsia-100 block">
              ⛔ NO TRAVEL ADVISED
            </strong>
            <span>
              Contains {noTravelMiles.toFixed(1)} mi of impassable weather or heavy-load wind restrictions.
            </span>
          </div>
        </div>
      )}

      {/* Key Metrics Row */}
      <div className="grid grid-cols-3 gap-2 py-2 border-y border-slate-800/80 mb-3 text-xs">
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-medium flex items-center gap-1">
            <Navigation className="w-2.5 h-2.5 text-[#f9564f]" /> Distance
          </span>
          <span className="font-semibold text-slate-200 text-xs">
            {formatDistance(totalDistance)}
          </span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-medium flex items-center gap-1">
            <Clock className="w-2.5 h-2.5 text-[#f9564f]" /> Duration
          </span>
          <span className="font-semibold text-slate-200 text-xs">
            {formatDuration(summary.total_duration_minutes)}
          </span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-medium flex items-center gap-1">
            <Calendar className="w-2.5 h-2.5 text-[#f9564f]" /> ETA
          </span>
          <span className="font-semibold text-slate-200 text-[11px] truncate block">
            {formatETA(summary.eta)}
          </span>
        </div>
      </div>

      {/* Risk Mileage Stacked Bar */}
      <div className="space-y-1.5 mb-2.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400 font-medium">Risk Mileage Distribution</span>
          <span className="text-slate-400 flex items-center gap-1 text-[10px]">
            <Activity className="w-3 h-3 text-[#f9564f]" />
            Avg Risk: <strong className="text-slate-200">{avgRisk}</strong>
          </span>
        </div>

        {/* Stacked Progress Bar */}
        <div
          className="h-2.5 w-full rounded-full overflow-hidden flex bg-slate-800 shadow-inner"
          title={`Low: ${lowMiles}mi, Mod: ${moderateMiles}mi, High: ${highMiles}mi, Severe: ${severeMiles}mi, No Travel: ${noTravelMiles}mi`}
        >
          {pctNoTravel > 0 && (
            <div
              style={{ width: `${pctNoTravel}%`, backgroundColor: RISK_CONFIG['No Travel'].hex }}
              className="h-full transition-all"
              title={`No Travel: ${noTravelMiles.toFixed(1)} mi (${pctNoTravel.toFixed(0)}%)`}
            />
          )}
          {pctSevere > 0 && (
            <div
              style={{ width: `${pctSevere}%`, backgroundColor: RISK_CONFIG.Severe.hex }}
              className="h-full transition-all"
              title={`Severe: ${severeMiles.toFixed(1)} mi (${pctSevere.toFixed(0)}%)`}
            />
          )}
          {pctHigh > 0 && (
            <div
              style={{ width: `${pctHigh}%`, backgroundColor: RISK_CONFIG.High.hex }}
              className="h-full transition-all"
              title={`High: ${highMiles.toFixed(1)} mi (${pctHigh.toFixed(0)}%)`}
            />
          )}
          {pctModerate > 0 && (
            <div
              style={{ width: `${pctModerate}%`, backgroundColor: RISK_CONFIG.Moderate.hex }}
              className="h-full transition-all"
              title={`Moderate: ${moderateMiles.toFixed(1)} mi (${pctModerate.toFixed(0)}%)`}
            />
          )}
          {pctLow > 0 && (
            <div
              style={{ width: `${pctLow}%`, backgroundColor: RISK_CONFIG.Low.hex }}
              className="h-full transition-all"
              title={`Low: ${lowMiles.toFixed(1)} mi (${pctLow.toFixed(0)}%)`}
            />
          )}
        </div>
      </div>

      {/* Mileage Breakdown Pills */}
      <div className="flex flex-wrap gap-1 text-[10px]">
        {noTravelMiles > 0 && (
          <span className={`px-1.5 py-0.5 rounded font-medium ${RISK_CONFIG['No Travel'].badge}`}>
            ⛔ {noTravelMiles.toFixed(0)} mi No Travel
          </span>
        )}
        {severeMiles > 0 && (
          <span className={`px-1.5 py-0.5 rounded font-medium ${RISK_CONFIG.Severe.badge}`}>
            {severeMiles.toFixed(0)} mi Severe
          </span>
        )}
        {highMiles > 0 && (
          <span className={`px-1.5 py-0.5 rounded font-medium ${RISK_CONFIG.High.badge}`}>
            {highMiles.toFixed(0)} mi High
          </span>
        )}
        {moderateMiles > 0 && (
          <span className={`px-1.5 py-0.5 rounded font-medium ${RISK_CONFIG.Moderate.badge}`}>
            {moderateMiles.toFixed(0)} mi Mod
          </span>
        )}
        {lowMiles > 0 && (
          <span className={`px-1.5 py-0.5 rounded font-medium ${RISK_CONFIG.Low.badge}`}>
            {lowMiles.toFixed(0)} mi Low
          </span>
        )}
      </div>
    </div>
  );
};

export default RouteCard;
