import React, { useEffect, useRef, useMemo } from 'react';
import { Marker, Tooltip, useMap } from 'react-leaflet';
import L from 'leaflet';

// Custom pulsating truck marker icon
const createTruckIcon = () => {
  return L.divIcon({
    className: 'truck-pulse-marker',
    html: `
      <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 42px; height: 42px;">
        <span style="position: absolute; width: 42px; height: 42px; border-radius: 9999px; background-color: rgba(56, 189, 248, 0.4); animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></span>
        <div style="position: relative; width: 32px; height: 32px; border-radius: 9999px; background-color: #0284c7; border: 2.5px solid #ffffff; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/>
            <path d="M15 18H9"/>
            <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/>
            <circle cx="17" cy="18" r="2"/>
            <circle cx="7" cy="18" r="2"/>
          </svg>
        </div>
      </div>
    `,
    iconSize: [42, 42],
    iconAnchor: [21, 21],
  });
};

const getWindColorRgb = (windMph) => {
  if (windMph >= 55) return [112, 26, 117]; // Magenta / No Travel
  if (windMph >= 45) return [220, 38, 38];   // Red / Severe
  if (windMph >= 35) return [249, 115, 22];  // Orange / High
  if (windMph >= 25) return [251, 191, 36];  // Amber / Moderate
  if (windMph >= 15) return [16, 185, 129];  // Emerald / Light
  return [56, 189, 248];                     // Cyan / Calm
};

const getPrecipColorRgb = (precipIn) => {
  if (precipIn > 1.0) return [112, 26, 117]; // Violent
  if (precipIn >= 0.5) return [220, 38, 38];  // Heavy
  if (precipIn >= 0.25) return [249, 115, 22]; // Moderate
  if (precipIn >= 0.1) return [59, 130, 246];  // Light
  if (precipIn > 0.01) return [56, 189, 248]; // Very Light
  return null;                               // No precip (transparent)
};

const getSnowColorRgb = (snowIn) => {
  if (snowIn > 3.0) return [112, 26, 117];  // No Travel (>3.0 in/h)
  if (snowIn >= 2.0) return [220, 38, 38];  // Severe (2.0–3.0 in/h)
  if (snowIn >= 1.0) return [168, 85, 247]; // High (1.0–2.0 in/h, Purple)
  if (snowIn >= 0.5) return [129, 140, 248]; // Moderate (0.5–1.0 in/h, Indigo)
  if (snowIn > 0.02) return [165, 243, 252]; // Light Snow (Cyan/Ice Blue)
  return null;
};

export const CorridorHeatmapLayer = ({
  heatmapGrid = [],
  forecastHour = 0,
  heatmapMode = 'wind',
  activeRoute = null,
  heatmapOpacity = 0.45,
}) => {
  const map = useMap();
  const canvasRef = useRef(null);

  // Redraw the smooth weather heatmap on HTML5 canvas whenever map moves or forecast hour changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !map) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const render = () => {
      const size = map.getSize();
      canvas.width = size.x;
      canvas.height = size.y;

      ctx.clearRect(0, 0, size.x, size.y);

      if (heatmapMode === 'off' || !heatmapGrid || heatmapGrid.length === 0) {
        return;
      }

      // Extract route coordinates to constrain weather radar naturally to the active highway corridor
      const routeCoords = activeRoute?.geometry?.coordinates || [];

      // Calculate both horizontal (col) and vertical (row) distances to bridge elongated trip corridors
      let cellPixelRadius = 75;
      if (heatmapGrid.length >= 7) {
        const [lon0, lat0] = heatmapGrid[0].coordinates || [];
        const [lon1, lat1] = heatmapGrid[1].coordinates || []; // adjacent column
        const [lon6, lat6] = heatmapGrid[6].coordinates || []; // adjacent row
        if (lat0 !== undefined && lat1 !== undefined && lat6 !== undefined) {
          const pt0 = map.latLngToContainerPoint([lat0, lon0]);
          const pt1 = map.latLngToContainerPoint([lat1, lon1]);
          const pt6 = map.latLngToContainerPoint([lat6, lon6]);
          const distX = Math.hypot(pt1.x - pt0.x, pt1.y - pt0.y);
          const distY = Math.hypot(pt6.x - pt0.x, pt6.y - pt0.y);
          const maxStep = Math.max(distX, distY);
          if (maxStep > 10) {
            cellPixelRadius = Math.max(60, maxStep * 1.35);
          }
        }
      }

      ctx.save();
      // Apply the user-controlled global opacity cleanly to the entire radar overlay
      ctx.globalAlpha = Math.max(0.05, Math.min(1.0, heatmapOpacity ?? 0.45));

      // Enhanced atmospheric blur eliminates discrete grid points and creates fluid weather clouds
      if (ctx.filter !== undefined) {
        ctx.filter = 'blur(28px)';
      }

      // Proximity helper: calculates distance from grid point to nearest route coordinate in miles
      const getDistToRouteMiles = (ptLat, ptLon) => {
        if (!routeCoords || routeCoords.length === 0) return 0;
        let minD = Infinity;
        const step = Math.max(1, Math.floor(routeCoords.length / 50));
        for (let i = 0; i < routeCoords.length; i += step) {
          const [rLon, rLat] = routeCoords[i];
          const d = Math.hypot(ptLat - rLat, (ptLon - rLon) * Math.cos((ptLat * Math.PI) / 180));
          if (d < minD) minD = d;
        }
        return minD * 69.0;
      };

      heatmapGrid.forEach((point) => {
        const [lon, lat] = point.coordinates || [];
        if (lat === undefined || lon === undefined) return;

        // Dim or skip grid points that fall too far into open water / outside the road corridor
        if (routeCoords.length > 0) {
          const distToRoute = getDistToRouteMiles(lat, lon);
          if (distToRoute > 160) {
            return; // Ignore points far in the open sea
          }
        }

        const containerPt = map.latLngToContainerPoint([lat, lon]);

        // Only draw points near visible screen area
        if (
          containerPt.x < -cellPixelRadius * 2 ||
          containerPt.x > size.x + cellPixelRadius * 2 ||
          containerPt.y < -cellPixelRadius * 2 ||
          containerPt.y > size.y + cellPixelRadius * 2
        ) {
          return;
        }

        let rgb = null;
        let baseAlpha = 0.55;

        if (heatmapMode === 'wind') {
          const windMph = point.hourly_wind_mph?.[forecastHour] || 0;
          rgb = getWindColorRgb(windMph);
          baseAlpha = windMph >= 45 ? 0.75 : windMph >= 25 ? 0.6 : 0.45;
        } else if (heatmapMode === 'precip') {
          const precipIn = point.hourly_precip_in?.[forecastHour] || 0;
          rgb = getPrecipColorRgb(precipIn);
          if (!rgb) return;
          baseAlpha = precipIn >= 0.5 ? 0.75 : precipIn >= 0.25 ? 0.6 : 0.45;
        } else if (heatmapMode === 'snow') {
          const snowIn = point.hourly_snow_in?.[forecastHour] || 0;
          rgb = getSnowColorRgb(snowIn);
          if (!rgb) return;
          baseAlpha = snowIn >= 2.0 ? 0.75 : snowIn >= 0.5 ? 0.6 : 0.45;
        }

        if (!rgb) return;

        // Smoothly fade intensity for points towards corridor edges
        if (routeCoords.length > 0) {
          const distToRoute = getDistToRouteMiles(lat, lon);
          if (distToRoute > 60) {
            const falloff = Math.max(0.1, 1 - (distToRoute - 60) / 100);
            baseAlpha *= falloff;
          }
        }

        const [r, g, b] = rgb;

        // Radial gradient with smooth, zero-opacity outer falloff
        const grad = ctx.createRadialGradient(
          containerPt.x,
          containerPt.y,
          0,
          containerPt.x,
          containerPt.y,
          cellPixelRadius
        );
        grad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${baseAlpha})`);
        grad.addColorStop(0.35, `rgba(${r}, ${g}, ${b}, ${baseAlpha * 0.7})`);
        grad.addColorStop(0.7, `rgba(${r}, ${g}, ${b}, ${baseAlpha * 0.25})`);
        grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(containerPt.x, containerPt.y, cellPixelRadius, 0, Math.PI * 2);
        ctx.fill();
      });

      ctx.restore();
    };

    render();

    map.on('move', render);
    map.on('zoom', render);
    map.on('resize', render);

    return () => {
      map.off('move', render);
      map.off('zoom', render);
      map.off('resize', render);
    };
  }, [map, heatmapGrid, forecastHour, heatmapMode, heatmapOpacity]);

  // Calculate truck position along active route at departureTime + forecastHour
  const truckState = useMemo(() => {
    if (!activeRoute) return null;

    const coords = activeRoute.geometry?.coordinates;
    const checkpoints = activeRoute.checkpoints;
    const totalDurationMin = activeRoute.summary?.total_duration_minutes || 0;
    const totalDistanceMiles = activeRoute.summary?.total_distance_miles || 0;

    if (!coords || coords.length === 0) return null;

    const elapsedMinutes = forecastHour * 60;

    // Check if arrived
    if (totalDurationMin > 0 && elapsedMinutes >= totalDurationMin) {
      const [endLon, endLat] = coords[coords.length - 1];
      return {
        lat: endLat,
        lon: endLon,
        mile: totalDistanceMiles,
        isArrived: true,
        progressPct: 100,
      };
    }

    // Check if at start
    if (elapsedMinutes <= 0) {
      const [startLon, startLat] = coords[0];
      return {
        lat: startLat,
        lon: startLon,
        mile: 0,
        isArrived: false,
        progressPct: 0,
      };
    }

    const progressRatio = Math.max(0, Math.min(1, elapsedMinutes / totalDurationMin));
    const targetMile = progressRatio * totalDistanceMiles;

    if (checkpoints && checkpoints.length >= 2) {
      for (let i = 0; i < checkpoints.length - 1; i++) {
        const cpA = checkpoints[i];
        const cpB = checkpoints[i + 1];

        if (targetMile >= cpA.mile_marker && targetMile <= cpB.mile_marker) {
          const segmentDist = cpB.mile_marker - cpA.mile_marker;
          const ratio = segmentDist > 0 ? (targetMile - cpA.mile_marker) / segmentDist : 0;

          const [lonA, latA] = cpA.coordinates;
          const [lonB, latB] = cpB.coordinates;

          return {
            lat: latA + ratio * (latB - latA),
            lon: lonA + ratio * (lonB - lonA),
            mile: targetMile,
            isArrived: false,
            progressPct: progressRatio * 100,
          };
        }
      }
    }

    const targetIdx = Math.floor(progressRatio * (coords.length - 1));
    const [lon, lat] = coords[targetIdx];
    return {
      lat,
      lon,
      mile: targetMile,
      isArrived: false,
      progressPct: progressRatio * 100,
    };
  }, [activeRoute, forecastHour]);

  const truckMarkerIcon = useMemo(() => createTruckIcon(), []);

  return (
    <>
      {/* 1. Seamless Canvas Weather Radar Overlay */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: 450,
        }}
      />

      {/* 2. Truck Live Position Marker */}
      {truckState && (
        <Marker
          position={[truckState.lat, truckState.lon]}
          icon={truckMarkerIcon}
          zIndexOffset={1000}
        >
          <Tooltip direction="top" offset={[0, -22]} permanent={false} opacity={0.95}>
            <div className="text-xs font-sans p-1">
              <div className="font-bold text-sky-400 flex items-center gap-1">
                <span>🚛 Truck Position (+{forecastHour}h)</span>
              </div>
              <div className="text-slate-300 mt-0.5">
                Mile {truckState.mile.toFixed(1)} / {activeRoute?.summary?.total_distance_miles?.toFixed(1)} mi ({truckState.progressPct.toFixed(0)}%)
              </div>
              {truckState.isArrived && (
                <div className="text-emerald-400 font-semibold mt-0.5">
                  ✓ Arrived at destination
                </div>
              )}
            </div>
          </Tooltip>
        </Marker>
      )}
    </>
  );
};

export default CorridorHeatmapLayer;
