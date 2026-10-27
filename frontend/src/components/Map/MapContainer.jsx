import React, { useEffect, useMemo } from 'react';
import {
  MapContainer as LeafletMap,
  TileLayer,
  Polyline,
  CircleMarker,
  Popup,
  Tooltip,
  useMap,
} from 'react-leaflet';
import CheckpointPopup from './CheckpointPopup';
import { RISK_CONFIG, getRiskConfig } from '../../utils/riskColors';

// Auto-adjusts camera to fit the corridor bounding box or active routes
const BoundsFitter = ({ bbox, routes }) => {
  const map = useMap();

  useEffect(() => {
    if (!map) return;

    if (bbox && Array.isArray(bbox) && bbox.length === 4) {
      const [minLng, minLat, maxLng, maxLat] = bbox;
      if (
        !isNaN(minLng) &&
        !isNaN(minLat) &&
        !isNaN(maxLng) &&
        !isNaN(maxLat) &&
        (minLng !== maxLng || minLat !== maxLat)
      ) {
        map.fitBounds(
          [
            [minLat, minLng],
            [maxLat, maxLng],
          ],
          { padding: [50, 50], maxZoom: 12, animate: true }
        );
        return;
      }
    }

    // Fallback: derive bounds from all available route coordinates
    if (routes && routes.length > 0) {
      const allPoints = [];
      routes.forEach((r) => {
        if (r.geometry && r.geometry.coordinates) {
          r.geometry.coordinates.forEach(([lon, lat]) => {
            allPoints.push([lat, lon]);
          });
        }
      });

      if (allPoints.length > 0) {
        map.fitBounds(allPoints, { padding: [50, 50], maxZoom: 12, animate: true });
      }
    }
  }, [bbox, routes, map]);

  return null;
};

export const MapContainer = ({
  routes = [],
  selectedRouteId = null,
  onSelectRoute,
  corridorBbox = null,
  children,
}) => {
  const activeRoute = useMemo(() => {
    if (!routes || routes.length === 0) return null;
    return routes.find((r) => r.id === selectedRouteId) || routes[0];
  }, [routes, selectedRouteId]);

  // Leaflet map center defaults to Geographic Center of Contiguous US
  const initialCenter = [39.8283, -98.5795];
  const initialZoom = 4;

  return (
    <div className="w-full h-full relative overflow-hidden bg-slate-950">
      <LeafletMap
        center={initialCenter}
        zoom={initialZoom}
        scrollWheelZoom={true}
        className="w-full h-full z-0"
      >
        <TileLayer
          attribution='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          maxZoom={16}
        />

        <BoundsFitter bbox={corridorBbox} routes={routes} />

        {/* 1. Inactive Routes (rendered in background) */}
        {routes.map((route) => {
          const isSelected = activeRoute && activeRoute.id === route.id;
          if (isSelected) return null; // Rendered separately on top

          const latLngs = (route.geometry?.coordinates || []).map(([lon, lat]) => [lat, lon]);
          if (latLngs.length === 0) return null;

          return (
            <Polyline
              key={route.id}
              positions={latLngs}
              pane="markerPane"
              pathOptions={{
                color: '#64748b',
                weight: 4,
                opacity: 0.45,
                lineCap: 'round',
                lineJoin: 'round',
              }}
              eventHandlers={{
                click: () => onSelectRoute?.(route.id),
              }}
            >
              <Tooltip sticky>
                <div className="text-xs font-sans">
                  <strong>{route.name}</strong>
                  <div className="text-slate-400">Click to inspect route</div>
                </div>
              </Tooltip>
            </Polyline>
          );
        })}

        {/* 2. Selected Active Route (rendered on top with distinct color) */}
        {activeRoute && activeRoute.geometry?.coordinates && (
          <Polyline
            key={`active-${activeRoute.id}`}
            positions={activeRoute.geometry.coordinates.map(([lon, lat]) => [lat, lon])}
            pane="markerPane"
            pathOptions={{
              color: activeRoute.is_recommended
                ? '#10b981' // Emerald
                : activeRoute.summary?.no_travel_miles > 0
                ? '#e11d48' // Rose / Red alert
                : '#38bdf8', // Sky Blue
              weight: 6,
              opacity: 0.95,
              lineCap: 'round',
              lineJoin: 'round',
            }}
          />
        )}

        {/* 3. Checkpoint CircleMarkers along Active Route */}
        {activeRoute &&
          activeRoute.checkpoints &&
          activeRoute.checkpoints.map((cp) => {
            const [lon, lat] = cp.coordinates || [];
            if (lat === undefined || lon === undefined) return null;

            const riskCfg = getRiskConfig(cp.overall_risk);
            const isNoTravel = cp.overall_risk === 'No Travel';

            return (
              <CircleMarker
                key={`cp-${activeRoute.id}-${cp.index}`}
                center={[lat, lon]}
                pane="markerPane"
                radius={isNoTravel ? 7 : 5.5}
                pathOptions={{
                  fillColor: riskCfg.hex,
                  fillOpacity: 0.95,
                  color: isNoTravel ? '#ffffff' : '#0f172a',
                  weight: isNoTravel ? 2.5 : 1.5,
                }}
              >
                <Popup closeButton={false} offset={[0, -4]}>
                  <CheckpointPopup checkpoint={cp} />
                </Popup>
                <Tooltip direction="top" offset={[0, -6]} opacity={0.9}>
                  <span className="text-[10px] font-bold">
                    Mile {cp.mile_marker}: {cp.overall_risk}
                  </span>
                </Tooltip>
              </CircleMarker>
            );
          })}

        {/* 4. Origin & Destination Pin Markers */}
        {activeRoute && activeRoute.geometry?.coordinates && activeRoute.geometry.coordinates.length > 0 && (
          <>
            {/* Origin Pin */}
            {(() => {
              const [startLon, startLat] = activeRoute.geometry.coordinates[0];
              return (
                <CircleMarker
                  center={[startLat, startLon]}
                  pane="markerPane"
                  radius={8}
                  pathOptions={{
                    fillColor: '#10b981',
                    fillOpacity: 1,
                    color: '#ffffff',
                    weight: 3,
                  }}
                >
                  <Tooltip permanent direction="bottom" offset={[0, 8]}>
                    <span className="text-[10px] font-bold bg-slate-900 px-1.5 py-0.5 rounded text-emerald-300">
                      ORIGIN
                    </span>
                  </Tooltip>
                </CircleMarker>
              );
            })()}

            {/* Destination Pin */}
            {(() => {
              const coords = activeRoute.geometry.coordinates;
              const [endLon, endLat] = coords[coords.length - 1];
              return (
                <CircleMarker
                  center={[endLat, endLon]}
                  pane="markerPane"
                  radius={8}
                  pathOptions={{
                    fillColor: '#38bdf8',
                    fillOpacity: 1,
                    color: '#ffffff',
                    weight: 3,
                  }}
                >
                  <Tooltip permanent direction="bottom" offset={[0, 8]}>
                    <span className="text-[10px] font-bold bg-slate-900 px-1.5 py-0.5 rounded text-sky-300">
                      DESTINATION
                    </span>
                  </Tooltip>
                </CircleMarker>
              );
            })()}
          </>
        )}

        {/* Additional layers (e.g. 0-48h Corridor Heatmap layer, Truck marker) */}
        {children}
      </LeafletMap>
    </div>
  );
};

export default MapContainer;
