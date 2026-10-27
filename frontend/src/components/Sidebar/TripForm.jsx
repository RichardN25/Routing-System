import React, { useState, useId, useRef } from 'react';
import {
  MapPin,
  Navigation,
  Calendar,
  Weight,
  Loader2,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import LocationAutocompleteInput from './LocationAutocompleteInput';

const PRESETS = [
  { label: 'Empty', weight: 15000, description: '15,000 lbs' },
  { label: 'Standard', weight: 34000, description: '34,000 lbs' },
  { label: 'Heavy', weight: 44000, description: '44,000 lbs' },
];

const getDefaultDepartureTime = () => {
  const now = new Date();
  // Round up to nearest 15 minutes for clean scheduling
  now.setMinutes(Math.ceil(now.getMinutes() / 15) * 15, 0, 0);
  const tzOffset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - tzOffset).toISOString().slice(0, 16);
};

export const TripForm = ({ onSubmit, isLoading = false, initialValues = {} }) => {
  const originId = useId();
  const destinationId = useId();
  const departureId = useId();
  const weightId = useId();
  const departureInputRef = useRef(null);

  const [origin, setOrigin] = useState(initialValues.origin || 'Chicago, IL');
  const [destination, setDestination] = useState(initialValues.destination || 'Denver, CO');
  const [departureTime, setDepartureTime] = useState(
    initialValues.departureTime || getDefaultDepartureTime()
  );
  const [loadWeightLbs, setLoadWeightLbs] = useState(
    initialValues.loadWeightLbs !== undefined ? initialValues.loadWeightLbs : 44000
  );
  const [validationError, setValidationError] = useState('');

  const numericWeight = Number(loadWeightLbs) || 0;

  const getLoadRuleHint = (weight) => {
    if (weight > 40000) {
      return {
        type: 'heavy',
        badge: 'Heavy Load Rules Active (>40,000 lbs)',
        detail: '35–44 mph wind escalates to Severe; 45+ mph wind triggers No Travel.',
        borderClass: 'border-amber-500/50 bg-[#141414] text-amber-200',
        icon: AlertTriangle,
      };
    }
    if (weight > 30000) {
      return {
        type: 'moderate',
        badge: 'Moderate Load Rules Active (>30,000 lbs)',
        detail: '45–54 mph wind escalates to No Travel.',
        borderClass: 'border-yellow-500/40 bg-[#141414] text-yellow-200',
        icon: AlertTriangle,
      };
    }
    return {
      type: 'standard',
      badge: 'Light / Empty Load (≤30,000 lbs)',
      detail: 'Base thresholds apply. 55+ mph wind triggers No Travel.',
      borderClass: 'border-slate-700 bg-[#141414] text-slate-300',
      icon: CheckCircle2,
    };
  };

  const ruleHint = getLoadRuleHint(numericWeight);
  const RuleIcon = ruleHint.icon;

  const handleSubmit = (e) => {
    e.preventDefault();
    setValidationError('');

    if (!origin.trim()) {
      setValidationError('Please specify a departure origin location.');
      return;
    }
    if (!destination.trim()) {
      setValidationError('Please specify an arrival destination location.');
      return;
    }
    if (origin.trim().toLowerCase() === destination.trim().toLowerCase()) {
      setValidationError('Origin and destination cannot be the same location.');
      return;
    }
    if (numericWeight < 0 || numericWeight > 200000) {
      setValidationError('Please provide a valid load weight between 0 and 200,000 lbs.');
      return;
    }

    const isoDeparture = new Date(departureTime).toISOString();

    const payload = {
      origin: origin.trim(),
      destination: destination.trim(),
      departure_time: isoDeparture,
      departureTime: isoDeparture,
      load_weight_lbs: numericWeight,
      loadWeightLbs: numericWeight,
    };

    if (onSubmit) {
      onSubmit(payload);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Origin & Destination Autocomplete Inputs */}
      <div className="space-y-3 relative">
        {/* Origin */}
        <LocationAutocompleteInput
          id={originId}
          label="Origin"
          value={origin}
          onChange={setOrigin}
          placeholder="e.g. Chicago, IL or Manila"
          disabled={isLoading}
          icon={MapPin}
          iconColor="text-[#f9564f]"
          focusRing="focus:ring-[#f9564f]"
        />

        {/* Destination */}
        <LocationAutocompleteInput
          id={destinationId}
          label="Destination"
          value={destination}
          onChange={setDestination}
          placeholder="e.g. Denver, CO or Baguio"
          disabled={isLoading}
          icon={Navigation}
          iconColor="text-[#f9564f]"
          focusRing="focus:ring-[#f9564f]"
        />
      </div>

      {/* Departure Time */}
      <div>
        <label htmlFor={departureId} className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
          Departure Date & Time
        </label>
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              if (departureInputRef.current) {
                if (typeof departureInputRef.current.showPicker === 'function') {
                  departureInputRef.current.showPicker();
                } else {
                  departureInputRef.current.focus();
                }
              }
            }}
            disabled={isLoading}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#f9564f] hover:text-[#e04842] transition-colors cursor-pointer z-10 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            title="Open Calendar Picker"
          >
            <Calendar className="w-4 h-4" />
          </button>
          <input
            ref={departureInputRef}
            id={departureId}
            type="datetime-local"
            value={departureTime}
            onChange={(e) => setDepartureTime(e.target.value)}
            disabled={isLoading}
            className="w-full pl-9 pr-4 py-2 bg-[#3b3b3b] border border-neutral-600 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#f9564f] focus:border-transparent transition cursor-pointer"
            required
          />
        </div>
      </div>

      {/* Load Weight Section */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <label htmlFor={weightId} className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Load Weight (lbs)
          </label>
          <span className="text-xs text-slate-200">
            {numericWeight.toLocaleString()} lbs
          </span>
        </div>

        <div className="relative">
          <Weight className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#f9564f] pointer-events-none" />
          <input
            id={weightId}
            type="number"
            min="0"
            max="120000"
            step="500"
            value={loadWeightLbs}
            onChange={(e) => setLoadWeightLbs(e.target.value)}
            placeholder="e.g. 44000"
            disabled={isLoading}
            className="w-full pl-9 pr-4 py-2 bg-[#3b3b3b] border border-neutral-600 rounded-lg text-sm text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-[#f9564f] focus:border-transparent transition [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            required
          />
        </div>

        {/* Quick Presets */}
        <div className="grid grid-cols-3 gap-2">
          {PRESETS.map((preset) => {
            const isSelected = numericWeight === preset.weight;
            return (
              <button
                key={preset.label}
                type="button"
                onClick={() => setLoadWeightLbs(preset.weight)}
                disabled={isLoading}
                className={`py-1.5 px-2 rounded-lg text-xs transition-all text-center border ${
                  isSelected
                    ? 'bg-[#141414] border-[#f9564f] ring-2 ring-[#f9564f]/30 text-white font-bold shadow-sm'
                    : 'bg-[#141414] border-neutral-600 text-white hover:border-[#f9564f]/60 hover:text-[#f9564f]'
                }`}
              >
                <div>{preset.label}</div>
                <div className={`text-[10px] ${isSelected ? 'text-neutral-300' : 'text-neutral-400'}`}>
                  {preset.description}
                </div>
              </button>
            );
          })}
        </div>

        {/* Dynamic Load Rule Escalation Hint */}
        <div className={`p-2.5 rounded-lg border text-xs transition-colors ${ruleHint.borderClass}`}>
          <div className="flex items-start gap-2">
            <RuleIcon className="w-4 h-4 mt-0.5 shrink-0 text-[#f9564f]" />
            <div className="space-y-0.5">
              <div className="font-semibold text-xs">{ruleHint.badge}</div>
              <p className="text-[11px] opacity-90 leading-relaxed">{ruleHint.detail}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Validation Alert */}
      {validationError && (
        <div className="p-2.5 rounded-lg bg-red-900/30 border border-red-700/50 text-red-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-3 px-4 rounded-xl font-bold text-sm bg-[#f9564f] hover:bg-[#e04842] active:scale-[0.99] text-black shadow-lg shadow-[#141414]/50 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-black" />
            <span>Analyzing 3 Routes & Weather...</span>
          </>
        ) : (
          <span>Analyze Safe Routes</span>
        )}
      </button>
    </form>
  );
};

export default TripForm;
