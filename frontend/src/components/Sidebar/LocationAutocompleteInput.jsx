import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Loader2, X, ChevronRight } from 'lucide-react';
import { fetchLocationSuggestions } from '../../api/routeClient';

export const LocationAutocompleteInput = ({
  id,
  label,
  value,
  onChange,
  placeholder,
  disabled = false,
  icon: Icon = MapPin,
  iconColor = 'text-emerald-400',
  focusRing = 'focus:ring-emerald-500',
}) => {
  const [query, setQuery] = useState(value || '');
  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  const containerRef = useRef(null);
  const debounceTimerRef = useRef(null);

  // Sync external value changes
  useEffect(() => {
    setQuery(value || '');
  }, [value]);

  // Click-outside listener to close dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Handle input text changes with debounced search
  const handleInputChange = (e) => {
    const text = e.target.value;
    setQuery(text);
    onChange?.(text);
    setSelectedIndex(-1);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!text || text.trim().length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setIsOpen(true);

    debounceTimerRef.current = setTimeout(async () => {
      try {
        const results = await fetchLocationSuggestions(text);
        setSuggestions(results);
        setIsOpen(results.length > 0);
      } catch (err) {
        console.error('Failed to fetch suggestions:', err);
        setSuggestions([]);
      } finally {
        setIsLoading(false);
      }
    }, 280);
  };

  const handleSelect = (item) => {
    setQuery(item.label);
    onChange?.(item.label);
    setIsOpen(false);
    setSuggestions([]);
  };

  const handleClear = () => {
    setQuery('');
    onChange?.('');
    setSuggestions([]);
    setIsOpen(false);
  };

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (!isOpen || suggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === 'Enter') {
      if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
        e.preventDefault();
        handleSelect(suggestions[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative space-y-1">
      {label && (
        <label
          htmlFor={id}
          className="block text-xs font-semibold text-slate-300 uppercase tracking-wider"
        >
          {label}
        </label>
      )}

      <div className="relative">
        <Icon className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${iconColor}`} />

        <input
          id={id}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0) setIsOpen(true);
          }}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          className={`w-full pl-9 pr-9 py-2.5 bg-[#3b3b3b] border border-neutral-600 rounded-lg text-sm text-white placeholder-neutral-400 focus:outline-none focus:ring-2 ${focusRing} focus:border-transparent transition`}
          required
        />

        {/* Right action button: Spinner or Clear */}
        <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center">
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-[#f9564f]" />
          ) : query ? (
            <button
              type="button"
              onClick={handleClear}
              disabled={disabled}
              className="p-1 rounded-full text-neutral-400 hover:text-[#f9564f] hover:bg-neutral-700 transition"
              title="Clear input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          ) : null}
        </div>
      </div>

      {/* Autocomplete Dropdown Menu */}
      {isOpen && suggestions.length > 0 && (
        <ul className="absolute top-full left-0 right-0 z-50 mt-1 bg-[#3b3b3b] border border-neutral-600 rounded-xl shadow-2xl overflow-hidden divide-y divide-neutral-600/70 max-h-60 overflow-y-auto custom-scrollbar">
          {suggestions.map((item, idx) => {
            const isHighlighted = idx === selectedIndex;
            return (
              <li
                key={item.id}
                onClick={() => handleSelect(item)}
                onMouseEnter={() => setSelectedIndex(idx)}
                className={`px-3 py-2.5 flex items-start justify-between gap-2 cursor-pointer transition text-left ${
                  isHighlighted
                    ? 'bg-neutral-600 text-white'
                    : 'text-white hover:bg-neutral-600/60'
                }`}
              >
                <div className="flex items-start gap-2 overflow-hidden">
                  <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-[#f9564f]" />
                  <div className="truncate">
                    <span className="font-semibold text-xs block text-white truncate">
                      {item.name}
                    </span>
                    {item.subtext && (
                      <span className="text-[11px] text-neutral-300 block truncate">
                        {item.subtext}
                      </span>
                    )}
                  </div>
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-[#f9564f] shrink-0 mt-1" />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export default LocationAutocompleteInput;
