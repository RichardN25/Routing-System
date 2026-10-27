import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ShieldAlert, Wind, CloudRain, Snowflake, Info } from 'lucide-react';
import { RISK_CONFIG } from '../../utils/riskColors';

const TIERS = [
  {
    tier: 'Low',
    wind: '< 25 mph',
    rain: '< 0.10 in/h',
    snow: '< 0.5 in/h',
  },
  {
    tier: 'Moderate',
    wind: '25 – 34 mph',
    rain: '0.10 – 0.25 in/h',
    snow: '0.5 – 1.0 in/h',
  },
  {
    tier: 'High',
    wind: '35 – 44 mph',
    rain: '0.25 – 0.50 in/h',
    snow: '1.0 – 2.0 in/h',
  },
  {
    tier: 'Severe',
    wind: '45 – 54 mph',
    rain: '0.50 – 1.00 in/h',
    snow: '2.0 – 3.0 in/h',
  },
  {
    tier: 'No Travel',
    wind: '≥ 55 mph*',
    rain: '> 1.00 in/h',
    snow: '> 3.0 in/h',
  },
];

export const RiskLegend = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="rounded-xl border border-neutral-600 bg-[#3b3b3b] text-xs text-white overflow-hidden transition-all shadow-md">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-[#484848] transition-colors focus:outline-none"
        aria-expanded={isOpen}
      >
        <span className="flex items-center gap-2 font-medium text-white">
          <ShieldAlert className="w-4 h-4 text-[#f9564f]" />
          <span>Weather Risk & Load Escalation Legend</span>
        </span>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-[#f9564f]" />
        ) : (
          <ChevronDown className="w-4 h-4 text-[#f9564f]" />
        )}
      </button>

      {isOpen && (
        <div className="p-3 pt-0 border-t border-neutral-600/70 space-y-3">
          {/* Thresholds Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-neutral-600 text-[10px] uppercase text-neutral-300 font-semibold tracking-wider">
                  <th className="py-1.5 pr-2">Tier</th>
                  <th className="py-1.5 px-2">
                    <span className="flex items-center gap-1">
                      <Wind className="w-3 h-3 text-sky-400" /> Wind
                    </span>
                  </th>
                  <th className="py-1.5 px-2">
                    <span className="flex items-center gap-1">
                      <CloudRain className="w-3 h-3 text-blue-400" /> Rain
                    </span>
                  </th>
                  <th className="py-1.5 pl-2">
                    <span className="flex items-center gap-1">
                      <Snowflake className="w-3 h-3 text-cyan-200" /> Snow
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-600/50">
                {TIERS.map((row) => {
                  const cfg = RISK_CONFIG[row.tier];
                  return (
                    <tr key={row.tier} className="hover:bg-neutral-600/30">
                      <td className="py-1.5 pr-2 whitespace-nowrap">
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${cfg.badge}`}
                        >
                          {row.tier}
                        </span>
                      </td>
                      <td className="py-1.5 px-2 text-white text-[11px] whitespace-nowrap">
                        {row.wind}
                      </td>
                      <td className="py-1.5 px-2 text-white text-[11px] whitespace-nowrap">
                        {row.rain}
                      </td>
                      <td className="py-1.5 pl-2 text-white text-[11px] whitespace-nowrap">
                        {row.snow}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default RiskLegend;
