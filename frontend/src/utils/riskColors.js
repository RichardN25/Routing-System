export const RISK_CONFIG = {
  Low: {
    level: 0,
    label: 'Low',
    hex: '#10b981',
    bgClass: 'bg-emerald-500/20',
    textClass: 'text-emerald-400',
    borderClass: 'border-emerald-500/30',
    badge: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    badgeClass: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    description: 'Safe driving conditions with calm wind and clear weather.',
  },
  Moderate: {
    level: 1,
    label: 'Moderate',
    hex: '#fbbf24',
    bgClass: 'bg-amber-500/20',
    textClass: 'text-amber-400',
    borderClass: 'border-amber-500/30',
    badge: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
    badgeClass: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
    description: 'Caution advised; elevated wind gusts or light precipitation.',
  },
  High: {
    level: 2,
    label: 'High',
    hex: '#f97316',
    bgClass: 'bg-orange-500/20',
    textClass: 'text-orange-400',
    borderClass: 'border-orange-500/30',
    badge: 'bg-orange-500/10 text-orange-400 border border-orange-500/20',
    badgeClass: 'bg-orange-500/10 text-orange-400 border border-orange-500/20',
    description: 'Adverse weather requiring reduced speeds and high vigilance.',
  },
  Severe: {
    level: 3,
    label: 'Severe',
    hex: '#dc2626',
    bgClass: 'bg-red-500/20',
    textClass: 'text-red-400',
    borderClass: 'border-red-500/30',
    badge: 'bg-red-500/10 text-red-400 border border-red-500/20',
    badgeClass: 'bg-red-500/10 text-red-400 border border-red-500/20',
    description: 'Hazardous weather or heavy load wind escalation.',
  },
  'No Travel': {
    level: 4,
    label: 'No Travel',
    hex: '#701a75',
    bgClass: 'bg-fuchsia-950/80',
    textClass: 'text-fuchsia-300',
    borderClass: 'border-fuchsia-500',
    badge: 'bg-fuchsia-950 text-fuchsia-200 border border-fuchsia-500 font-semibold',
    badgeClass: 'bg-fuchsia-950 text-fuchsia-200 border border-fuchsia-500 font-semibold',
    description: 'Impassable weather or extreme wind risk for heavy loads. Do not travel.',
  },
};

export const LEVEL_TO_RISK = {
  0: 'Low',
  1: 'Moderate',
  2: 'High',
  3: 'Severe',
  4: 'No Travel',
};

export const getRiskConfig = (riskOrLevel) => {
  if (typeof riskOrLevel === 'number') {
    const key = LEVEL_TO_RISK[riskOrLevel] || 'Low';
    return RISK_CONFIG[key];
  }
  if (typeof riskOrLevel === 'string' && RISK_CONFIG[riskOrLevel]) {
    return RISK_CONFIG[riskOrLevel];
  }
  return RISK_CONFIG.Low;
};

export const formatDuration = (minutes) => {
  if (minutes === null || minutes === undefined || isNaN(minutes)) {
    return '0m';
  }
  const totalMinutes = Math.round(Number(minutes));
  const hours = Math.floor(totalMinutes / 60);
  const remainingMins = totalMinutes % 60;

  if (hours === 0) {
    return `${remainingMins}m`;
  }
  if (remainingMins === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${remainingMins}m`;
};

export const formatETA = (isoString) => {
  if (!isoString) return '--';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '--';
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return '--';
  }
};

export const formatDistance = (miles) => {
  if (miles === null || miles === undefined || isNaN(miles)) {
    return '0 mi';
  }
  return `${Number(miles).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  })} mi`;
};
