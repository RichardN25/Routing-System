import React from 'react';
import {
  Clock,
  Navigation,
  Wind,
  CloudRain,
  Snowflake,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react';
import { getRiskConfig } from '../../utils/riskColors';

export const CheckpointPopup = ({ checkpoint }) => {
  if (!checkpoint) return null;

  const {
    index = 0,
    mile_marker = 0,
    eta,
    weather = {},
    risk_breakdown = {},
    overall_risk = 'Low',
    triggered_load_rule,
  } = checkpoint;

  const riskConfig = getRiskConfig(overall_risk);

  const formattedEta = eta
    ? new Date(eta).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      })
    : '--';

  const windMph = weather.wind_mph !== undefined ? Number(weather.wind_mph).toFixed(1) : '0.0';
  const rainInHr = weather.rain_in_hr !== undefined ? Number(weather.rain_in_hr).toFixed(2) : '0.00';
  const snowInHr = weather.snow_in_hr !== undefined ? Number(weather.snow_in_hr).toFixed(2) : '0.00';

  const windRiskCfg = getRiskConfig(risk_breakdown.wind || 'Low');
  const rainRiskCfg = getRiskConfig(risk_breakdown.rain || 'Low');
  const snowRiskCfg = getRiskConfig(risk_breakdown.snow || 'Low');

  return (
    <div className="p-3.5 bg-slate-900 text-slate-100 rounded-xl min-w-[250px] max-w-[280px] space-y-3 font-sans shadow-2xl border border-slate-700/80">
      {/* Header: Checkpoint & Mile Marker */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-1.5">
          <Navigation className="w-3.5 h-3.5 text-sky-400" />
          <span className="font-bold text-xs text-slate-200">
            Mile {mile_marker}
          </span>
          <span className="text-[10px] text-slate-500">
            (#{index})
          </span>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${riskConfig.badge}`}>
          {riskConfig.label}
        </span>
      </div>

      {/* ETA row */}
      <div className="flex items-center gap-1.5 text-xs text-slate-300">
        <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span className="text-[11px]">{formattedEta}</span>
      </div>

      {/* Weather Metrics Grid */}
      <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
        {/* Wind */}
        <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/60">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-400 mb-0.5">
            <Wind className="w-3 h-3 text-sky-400" />
            <span>Wind</span>
          </div>
          <div className="text-xs font-bold text-slate-100">
            {windMph} <span className="text-[9px] font-normal text-slate-400">mph</span>
          </div>
          <div className={`text-[9px] font-medium mt-0.5 ${windRiskCfg.textClass}`}>
            {risk_breakdown.wind || 'Low'}
          </div>
        </div>

        {/* Rain */}
        <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/60">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-400 mb-0.5">
            <CloudRain className="w-3 h-3 text-blue-400" />
            <span>Rain</span>
          </div>
          <div className="text-xs font-bold text-slate-100">
            {rainInHr} <span className="text-[9px] font-normal text-slate-400">in/h</span>
          </div>
          <div className={`text-[9px] font-medium mt-0.5 ${rainRiskCfg.textClass}`}>
            {risk_breakdown.rain || 'Low'}
          </div>
        </div>

        {/* Snow */}
        <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/60">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-400 mb-0.5">
            <Snowflake className="w-3 h-3 text-cyan-200" />
            <span>Snow</span>
          </div>
          <div className="text-xs font-bold text-slate-100">
            {snowInHr} <span className="text-[9px] font-normal text-slate-400">in/h</span>
          </div>
          <div className={`text-[9px] font-medium mt-0.5 ${snowRiskCfg.textClass}`}>
            {risk_breakdown.snow || 'Low'}
          </div>
        </div>
      </div>

      {/* Triggered Load Rule Box (if any) */}
      {triggered_load_rule && (
        <div className="p-2 rounded-lg bg-amber-950/70 border border-amber-600/50 text-amber-200 text-[11px] flex items-start gap-1.5 shadow-sm">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5 leading-tight">
            <span className="font-bold block text-amber-100 text-[10px] uppercase tracking-wide">
              Load Escalation Triggered
            </span>
            <span>{triggered_load_rule}</span>
          </div>
        </div>
      )}

      {!triggered_load_rule && overall_risk === 'Low' && (
        <div className="flex items-center gap-1.5 text-[10px] text-emerald-400/90 pt-0.5">
          <ShieldCheck className="w-3 h-3" />
          <span>Optimal weather for commercial transit</span>
        </div>
      )}
    </div>
  );
};

export default CheckpointPopup;
