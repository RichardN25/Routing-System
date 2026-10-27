import React, { useState, useMemo, useCallback } from 'react';
import {
  AlertCircle,
  X,
  Layers,
  Activity,
  Loader2,
  Navigation,
  Clock,
  Weight,
} from 'lucide-react';
import TripForm from './components/Sidebar/TripForm';
import RouteCard from './components/Sidebar/RouteCard';
import RiskLegend from './components/Sidebar/RiskLegend';
import MapContainer from './components/Map/MapContainer';
import CorridorHeatmapLayer from './components/Map/CorridorHeatmapLayer';
import ForecastSlider from './components/Timeline/ForecastSlider';
import { analyzeRoutes } from './api/routeClient';
import { formatDuration, formatDistance } from './utils/riskColors';

function App() {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [forecastHour, setForecastHour] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [heatmapMode, setHeatmapMode] = useState('wind');
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.40);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastSubmittedTrip, setLastSubmittedTrip] = useState(null);

  // Derive the active route from selectedRouteId or default to recommended/first
  const activeRoute = useMemo(() => {
    if (!analysisResult?.routes || analysisResult.routes.length === 0) return null;
    return (
      analysisResult.routes.find((r) => r.id === selectedRouteId) ||
      analysisResult.routes.find((r) => r.is_recommended) ||
      analysisResult.routes[0]
    );
  }, [analysisResult, selectedRouteId]);

  // Handle route analysis form submission
  const handleAnalyze = useCallback(async (formPayload) => {
    setIsLoading(true);
    setError(null);
    setIsPlaying(false);
    setForecastHour(0);

    try {
      const data = await analyzeRoutes(formPayload);
      setAnalysisResult(data);
      setLastSubmittedTrip(formPayload);

      // Default to recommended route
      const recId = data.recommended_route_id || data.routes?.[0]?.id || null;
      setSelectedRouteId(recId);
    } catch (err) {
      console.error('Route analysis error:', err);
      const msg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        (err.response?.status === 400
          ? 'Validation failed. Please verify your origin, destination, and load weight.'
          : err.message || 'Unable to connect to routing & weather backend.');
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 font-sans questrial-regular">
      {/* 1. Global Header Bar */}
      <header className="h-14 bg-[#141414] border-b border-slate-800 px-4 flex items-center justify-center shrink-0 z-20 shadow-md">
        <h1 className="font-bold text-base tracking-wide text-white">
          Truck Routing System
        </h1>
      </header>

      {/* 2. Main Viewport: Sidebar + Map */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
        {/* Left Sidebar: Trip Form, Legend & Route Cards */}
        <aside className="w-full md:w-[420px] lg:w-[450px] bg-[#141414] border-r border-slate-800/90 flex flex-col z-10 shadow-2xl overflow-y-auto custom-scrollbar shrink-0 p-4 space-y-4">
          {/* Section: Trip Configuration Form */}
          <div className="space-y-2">
            <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Navigation className="w-3.5 h-3.5 text-[#f9564f]" />
              <span>Trip Configuration</span>
            </h2>
            <TripForm
              onSubmit={handleAnalyze}
              isLoading={isLoading}
              initialValues={{
                origin: lastSubmittedTrip?.origin || 'Chicago, IL',
                destination: lastSubmittedTrip?.destination || 'Denver, CO',
                loadWeightLbs: lastSubmittedTrip?.load_weight_lbs ?? 44000,
              }}
            />
          </div>

          {/* Section: Risk & Load Legend */}
          <RiskLegend />

          {/* Section: 3-Route Comparison */}
          {(analysisResult || isLoading) && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-[#f9564f]" />
                  <span>Route Options (3 Generated)</span>
                </h2>
                {analysisResult?.routes?.length > 0 && (
                  <span className="text-[10px] text-slate-400">
                    Ranked by Safety
                  </span>
                )}
              </div>

              {/* Loading Skeleton */}
              {isLoading && !analysisResult && (
                <div className="space-y-3 pt-2">
                  {[1, 2, 3].map((n) => (
                    <div
                      key={n}
                      className="p-4 rounded-xl border border-slate-800 bg-slate-850/50 animate-pulse space-y-2.5"
                    >
                      <div className="h-4 bg-slate-700/60 rounded w-2/3"></div>
                      <div className="h-3 bg-slate-700/40 rounded w-1/2"></div>
                      <div className="h-2 bg-slate-700/30 rounded w-full"></div>
                    </div>
                  ))}
                </div>
              )}

              {/* Render 3 Route Cards */}
              {analysisResult?.routes && analysisResult.routes.length > 0 && (
                <div className="space-y-3 pt-1">
                  {analysisResult.routes.map((route, idx) => (
                    <RouteCard
                      key={route.id}
                      route={route}
                      routeIndex={idx + 1}
                      isSelected={activeRoute?.id === route.id}
                      onSelect={setSelectedRouteId}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </aside>

        {/* Right Area: Interactive Map Viewport */}
        <main className="flex-1 relative h-full bg-slate-950 overflow-hidden">
          {/* Error Banner */}
          {error && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1500] max-w-[90%] w-[520px] bg-red-950/90 border border-red-500 text-red-200 px-4 py-3 rounded-xl shadow-2xl flex items-start justify-between gap-3 backdrop-blur">
              <div className="flex items-start gap-2.5 text-xs">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold block text-red-100">
                    Routing Analysis Error
                  </strong>
                  <span>{error}</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setError(null)}
                className="text-red-400 hover:text-white transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Top-Right Stacked Metrics (Sampling Interval, Load, Miles) */}
          {activeRoute && (
            <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2 items-end pointer-events-none">
              {/* Sampling Interval Badge */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#141414]/90 border border-slate-800 text-slate-200 text-xs shadow-xl backdrop-blur pointer-events-auto">
                <Activity className="w-3.5 h-3.5 text-[#f9564f]" />
                <span>
                  Sampling Interval:{' '}
                  <strong className="text-white">
                    {activeRoute.summary?.sample_interval_miles || 25} mi
                  </strong>
                </span>
              </div>

              {/* Active Load Weight */}
              {lastSubmittedTrip && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#141414]/90 border border-slate-800 text-slate-200 text-xs shadow-xl backdrop-blur pointer-events-auto">
                  <Weight className="w-3.5 h-3.5 text-[#f9564f]" />
                  <span>
                    Load:{' '}
                    <strong className="text-white">
                      {Number(lastSubmittedTrip.load_weight_lbs).toLocaleString()} lbs
                    </strong>
                  </span>
                </div>
              )}

              {/* Active Route Distance (Miles) */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#141414]/90 border border-slate-800 text-slate-200 text-xs shadow-xl backdrop-blur pointer-events-auto">
                <Navigation className="w-3.5 h-3.5 text-[#f9564f]" />
                <span>
                  Miles:{' '}
                  <strong className="text-white">
                    {formatDistance(activeRoute.summary?.total_distance_miles)}
                  </strong>
                </span>
              </div>
            </div>
          )}

          {/* Loading Indicator Overlay */}
          {isLoading && (
            <div className="absolute top-4 left-4 z-[1500] bg-[#141414]/95 border border-[#f9564f]/40 text-white px-3.5 py-2 rounded-xl shadow-xl flex items-center gap-2.5 text-xs backdrop-blur">
              <Loader2 className="w-4 h-4 animate-spin text-[#f9564f]" />
              <span>Analyzing routes, weather corridor, and load rules...</span>
            </div>
          )}

          {/* Leaflet Map Container */}
          <MapContainer
            routes={analysisResult?.routes || []}
            selectedRouteId={activeRoute?.id}
            onSelectRoute={setSelectedRouteId}
            corridorBbox={analysisResult?.corridor_bbox}
          >
            {/* 0-48h Corridor Heatmap Grid & Animated Truck Marker */}
            <CorridorHeatmapLayer
              heatmapGrid={analysisResult?.heatmap_grid || []}
              forecastHour={forecastHour}
              heatmapMode={heatmapMode}
              heatmapOpacity={heatmapOpacity}
              activeRoute={activeRoute}
            />
          </MapContainer>

          {/* Floating 0–48h Forecast Timeline Slider */}
          {analysisResult && (
            <ForecastSlider
              forecastHour={forecastHour}
              onChangeHour={setForecastHour}
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying((prev) => !prev)}
              departureTime={lastSubmittedTrip?.departure_time}
              heatmapMode={heatmapMode}
              onChangeMode={setHeatmapMode}
              heatmapOpacity={heatmapOpacity}
              onChangeOpacity={setHeatmapOpacity}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
