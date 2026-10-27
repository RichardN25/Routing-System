import React, { useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Wind,
  CloudRain,
  EyeOff,
  Clock,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  Snowflake,
} from 'lucide-react';

export const ForecastSlider = ({
  forecastHour = 0,
  onChangeHour,
  isPlaying = false,
  onTogglePlay,
  departureTime,
  heatmapMode = 'wind',
  onChangeMode,
  heatmapOpacity = 0.45,
  onChangeOpacity,
}) => {
  const timerRef = useRef(null);

  // Play animation loop (increments hour every 500ms)
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        onChangeHour?.((prev) => (prev >= 48 ? 0 : prev + 1));
      }, 500);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, onChangeHour]);

  // Calculate projected date/time for departureTime + forecastHour
  const getProjectedTime = () => {
    try {
      const base = departureTime ? new Date(departureTime) : new Date();
      if (isNaN(base.getTime())) return '--';
      const projected = new Date(base.getTime() + forecastHour * 60 * 60 * 1000);
      return projected.toLocaleString('en-US', {
        weekday: 'short',
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

  const handleSliderChange = (e) => {
    onChangeHour?.(Number(e.target.value));
  };

  const handleStep = (step) => {
    onChangeHour?.((prev) => {
      const next = prev + step;
      return Math.max(0, Math.min(48, next));
    });
  };

  const handleReset = () => {
    onChangeHour?.(0);
    if (isPlaying) onTogglePlay?.();
  };

  return (
    <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-[1000] w-[94%] max-w-[620px] bg-[#141414] backdrop-blur-md border border-slate-800 rounded-2xl p-4 shadow-2xl text-slate-100 space-y-3 font-sans questrial-regular select-none">
      {/* Top Row: Mode Toggle, Opacity Slider & Projected Time */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Heatmap Mode Toggle Pills */}
          <div className="flex items-center p-1 bg-[#3b3b3b] rounded-xl border border-neutral-600 text-xs font-medium">
            <button
              type="button"
              onClick={() => onChangeMode?.('wind')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all ${
                heatmapMode === 'wind'
                  ? 'bg-[#f9564f] text-black font-bold shadow-sm'
                  : 'text-white hover:text-[#f9564f]'
              }`}
            >
              <Wind className="w-3.5 h-3.5" />
              <span>Wind</span>
            </button>

            <button
              type="button"
              onClick={() => onChangeMode?.('precip')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all ${
                heatmapMode === 'precip'
                  ? 'bg-[#f9564f] text-black font-bold shadow-sm'
                  : 'text-white hover:text-[#f9564f]'
              }`}
            >
              <CloudRain className="w-3.5 h-3.5" />
              <span>Rain/Precip</span>
            </button>

            <button
              type="button"
              onClick={() => onChangeMode?.('snow')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all ${
                heatmapMode === 'snow'
                  ? 'bg-[#f9564f] text-black font-bold shadow-sm'
                  : 'text-white hover:text-[#f9564f]'
              }`}
            >
              <Snowflake className="w-3.5 h-3.5" />
              <span>Snow</span>
            </button>

            <button
              type="button"
              onClick={() => onChangeMode?.('off')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all ${
                heatmapMode === 'off'
                  ? 'bg-[#f9564f] text-black font-bold shadow-sm'
                  : 'text-white hover:text-[#f9564f]'
              }`}
            >
              <EyeOff className="w-3.5 h-3.5" />
              <span>Off</span>
            </button>
          </div>

          {/* Opacity Slider Control (visible when mode is not off) */}
          {heatmapMode !== 'off' && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[#3b3b3b] rounded-xl border border-neutral-600 text-xs text-white">
              <SlidersHorizontal className="w-3 h-3 text-[#f9564f]" />
              <span className="text-[10px] text-white font-medium">Opacity</span>
              <input
                type="range"
                min="10"
                max="100"
                step="5"
                value={Math.round((heatmapOpacity ?? 0.45) * 100)}
                onChange={(e) => onChangeOpacity?.(Number(e.target.value) / 100)}
                className="w-16 h-1.5 bg-neutral-600 rounded-lg appearance-none cursor-pointer accent-[#f9564f]"
                title={`Radar Opacity: ${Math.round((heatmapOpacity ?? 0.45) * 100)}%`}
              />
              <span className="text-[10px] text-white w-6 text-right">
                {Math.round((heatmapOpacity ?? 0.45) * 100)}%
              </span>
            </div>
          )}
        </div>

        {/* Projected Clock Timestamp */}
        <div className="flex items-center gap-2 text-xs bg-[#3b3b3b] px-3 py-1.5 rounded-xl border border-neutral-600 text-white">
          <Clock className="w-3.5 h-3.5 text-[#f9564f] shrink-0" />
          <span className="text-[#f9564f] font-bold">+{forecastHour}h</span>
          <span className="text-neutral-400">|</span>
          <span className="text-white">{getProjectedTime()}</span>
        </div>
      </div>

      {/* Middle Row: Play Controls & Scrub Slider */}
      <div className="flex items-center gap-3">
        {/* Play/Pause Button */}
        <button
          type="button"
          onClick={onTogglePlay}
          title={isPlaying ? 'Pause Timeline' : 'Play 48h Timeline'}
          className="p-2.5 rounded-xl font-bold transition shadow-md flex items-center justify-center shrink-0 bg-[#f9564f] hover:bg-[#e04842] text-black ring-2 ring-[#f9564f]/40"
        >
          {isPlaying ? <Pause className="w-4 h-4 fill-current text-black" /> : <Play className="w-4 h-4 fill-current ml-0.5 text-black" />}
        </button>

        {/* Step Backward (-1h) */}
        <button
          type="button"
          onClick={() => handleStep(-1)}
          disabled={forecastHour <= 0}
          title="Previous Hour (-1h)"
          className="p-1.5 rounded-lg bg-[#3b3b3b] hover:bg-neutral-600 text-[#f9564f] disabled:opacity-30 disabled:cursor-not-allowed border border-neutral-600"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Range Slider */}
        <div className="flex-1 relative flex items-center">
          <input
            type="range"
            min="0"
            max="48"
            step="1"
            value={forecastHour}
            onChange={handleSliderChange}
            className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-[#f9564f] focus:outline-none"
          />
        </div>

        {/* Step Forward (+1h) */}
        <button
          type="button"
          onClick={() => handleStep(1)}
          disabled={forecastHour >= 48}
          title="Next Hour (+1h)"
          className="p-1.5 rounded-lg bg-[#3b3b3b] hover:bg-neutral-600 text-[#f9564f] disabled:opacity-30 disabled:cursor-not-allowed border border-neutral-600"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        {/* Reset to 0h */}
        <button
          type="button"
          onClick={handleReset}
          title="Reset to Departure (+0h)"
          className="p-1.5 rounded-lg bg-[#3b3b3b] hover:bg-neutral-600 text-[#f9564f] hover:text-white border border-neutral-600 transition"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Ticks & Helper Legend */}
      <div className="flex justify-between items-center text-[10px] text-slate-400 px-1">
        <span>0h (Departure)</span>
        <span>12h</span>
        <span>24h (Day 1)</span>
        <span>36h</span>
        <span>48h (Day 2)</span>
      </div>
    </div>
  );
};

export default ForecastSlider;
