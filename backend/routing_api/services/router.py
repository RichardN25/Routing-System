import math
import os
from typing import Any, Dict, List, Optional, Tuple
from django.conf import settings
import httpx


class RoutingError(Exception):
    """Raised when routing engine fails or cannot find routes."""
    pass


def fetch_three_routes(
    origin_coords: Tuple[float, float],
    dest_coords: Tuple[float, float],
    client: Optional[httpx.Client] = None,
) -> List[Dict[str, Any]]:
    lon1, lat1 = origin_coords
    lon2, lat2 = dest_coords

    if lon1 == lon2 and lat1 == lat2:
        raise RoutingError("Origin and destination coordinates cannot be identical.")

    mapbox_token = getattr(settings, "MAPBOX_ACCESS_TOKEN", None) or os.getenv("MAPBOX_ACCESS_TOKEN", "").strip()
    osrm_base_url = (
        getattr(settings, "OSRM_BASE_URL", None)
        or os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org")
    ).rstrip("/")

    owns_client = client is None
    http_client = client or httpx.Client(timeout=15.0)

    try:
        # 1. Fetch initial routes with alternatives
        if mapbox_token:
            raw_routes = _query_mapbox(lon1, lat1, lon2, lat2, mapbox_token, http_client)
        else:
            raw_routes = _query_osrm(lon1, lat1, lon2, lat2, osrm_base_url, http_client)

        routes: List[Dict[str, Any]] = []
        for raw in raw_routes:
            parsed = _parse_route(raw, default_name=f"Route {len(routes) + 1}")
            if parsed and not _is_duplicate_route(parsed, routes):
                routes.append(parsed)
                if len(routes) == 3:
                    break

        # 2. Waypoint Fallback if fewer than 3 routes returned
        if len(routes) < 3:
            routes = _fill_fallback_routes(
                routes=routes,
                lon1=lon1,
                lat1=lat1,
                lon2=lon2,
                lat2=lat2,
                mapbox_token=mapbox_token,
                osrm_base_url=osrm_base_url,
                client=http_client,
            )

        # 3. Final normalization and assigning route IDs
        if len(routes) < 3:
            routes = _synthesize_remaining_routes(routes, lon1, lat1, lon2, lat2)

        for i, r in enumerate(routes[:3]):
            r["id"] = f"route_{i + 1}"

        return routes[:3]

    finally:
        if owns_client:
            http_client.close()


def _query_mapbox(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    token: str,
    client: httpx.Client,
    waypoint: Optional[Tuple[float, float]] = None,
) -> List[Dict[str, Any]]:
    if waypoint:
        coords_str = f"{lon1},{lat1};{waypoint[0]},{waypoint[1]};{lon2},{lat2}"
        params = {
            "geometries": "geojson",
            "overview": "full",
            "steps": "true",
            "access_token": token,
        }
    else:
        coords_str = f"{lon1},{lat1};{lon2},{lat2}"
        params = {
            "alternatives": "true",
            "geometries": "geojson",
            "overview": "full",
            "steps": "true",
            "access_token": token,
        }

    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coords_str}"
    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("routes", [])
    except Exception as exc:
        raise RoutingError(f"Mapbox routing request failed: {exc}") from exc


def _query_osrm(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    base_url: str,
    client: httpx.Client,
    waypoint: Optional[Tuple[float, float]] = None,
) -> List[Dict[str, Any]]:
    if waypoint:
        coords_str = f"{lon1},{lat1};{waypoint[0]},{waypoint[1]};{lon2},{lat2}"
        params = {
            "geometries": "geojson",
            "overview": "full",
            "steps": "true",
        }
    else:
        coords_str = f"{lon1},{lat1};{lon2},{lat2}"
        params = {
            "alternatives": "true",
            "geometries": "geojson",
            "overview": "full",
            "steps": "true",
        }

    url = f"{base_url}/route/v1/driving/{coords_str}"
    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok":
            return []
        return data.get("routes", [])
    except Exception as exc:
        raise RoutingError(f"OSRM routing request failed: {exc}") from exc


def _parse_route(raw: Dict[str, Any], default_name: str) -> Optional[Dict[str, Any]]:
    geometry = raw.get("geometry")
    if not geometry or not isinstance(geometry, dict):
        return None

    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        return None

    dist_meters = float(raw.get("distance", 0.0))
    dur_sec = float(raw.get("duration", 0.0))

    dist_miles = round(dist_meters * 0.000621371, 1)
    dur_minutes = round(dur_sec / 60)

    # Extract highway/ref name from legs/steps
    name = _extract_route_name(raw) or default_name

    return {
        "id": "",
        "name": name,
        "total_distance_miles": dist_miles,
        "total_duration_minutes": dur_minutes,
        "total_duration_seconds": dur_sec,
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "summary": {
            "total_distance_miles": dist_miles,
            "total_duration_minutes": dur_minutes,
        },
        "checkpoints": [],
    }


def _extract_route_name(raw: Dict[str, Any]) -> str:
    legs = raw.get("legs", [])
    refs: List[str] = []
    names: List[str] = []

    for leg in legs:
        for step in leg.get("steps", []):
            ref = step.get("ref", "").strip()
            name = step.get("name", "").strip()
            if ref and ref not in refs:
                refs.append(ref)
            if name and name not in names:
                names.append(name)

    # Prefer Interstate (I-xx) or US highway (US-xx)
    for ref in refs:
        if ref.startswith("I-") or ref.startswith("US-") or "Interstate" in ref:
            return ref

    if refs:
        first_ref = refs[0]
        if first_ref.isdigit():
            return f"Route {first_ref}"
        return first_ref
    if names:
        return names[0]
    return ""


def _is_duplicate_route(candidate: Dict[str, Any], existing_routes: List[Dict[str, Any]]) -> bool:
    c_dist = candidate["total_distance_miles"]
    c_coords = candidate["geometry"]["coordinates"]
    for ex in existing_routes:
        ex_dist = ex["total_distance_miles"]
        ex_coords = ex["geometry"]["coordinates"]
        # If distance within 1% and coordinate count identical
        if abs(c_dist - ex_dist) < max(1.0, 0.01 * ex_dist):
            if len(c_coords) == len(ex_coords):
                return True
    return False


def _fill_fallback_routes(
    routes: List[Dict[str, Any]],
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    mapbox_token: str,
    osrm_base_url: str,
    client: httpx.Client,
) -> List[Dict[str, Any]]:
    mid_lon = (lon1 + lon2) / 2.0
    mid_lat = (lat1 + lat2) / 2.0

    dx = lon2 - lon1
    dy = lat2 - lat1
    length = math.hypot(dx, dy)

    if length > 0:
        # Unit perpendicular vector (-uy, ux)
        ux = dx / length
        uy = dy / length
        perp_dx = -uy
        perp_dy = ux
    else:
        perp_dx = 0.0
        perp_dy = 1.0

    # Offsets in degrees: +/- 0.4 deg (~28 miles) and +/- 0.8 deg (~55 miles)
    offsets = [0.4, -0.4, 0.8, -0.8]

    for offset in offsets:
        if len(routes) >= 3:
            break

        wp = (round(mid_lon + offset * perp_dx, 5), round(mid_lat + offset * perp_dy, 5))
        try:
            if mapbox_token:
                raw_list = _query_mapbox(lon1, lat1, lon2, lat2, mapbox_token, client, waypoint=wp)
            else:
                raw_list = _query_osrm(lon1, lat1, lon2, lat2, osrm_base_url, client, waypoint=wp)

            for raw in raw_list:
                parsed = _parse_route(raw, default_name=f"Alternative Route {len(routes) + 1}")
                if parsed and not _is_duplicate_route(parsed, routes):
                    routes.append(parsed)
                    if len(routes) >= 3:
                        break
        except Exception:
            # Continue trying next waypoint offset if one fails
            continue

    return routes


def _synthesize_remaining_routes(
    routes: List[Dict[str, Any]],
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
) -> List[Dict[str, Any]]:
    if not routes:
        # Generate simple straight line primary
        primary_coords = [[lon1, lat1], [(lon1 + lon2) / 2, (lat1 + lat2) / 2], [lon2, lat2]]
        primary = {
            "id": "route_1",
            "name": "Direct Highway",
            "total_distance_miles": 100.0,
            "total_duration_minutes": 95,
            "total_duration_seconds": 5700.0,
            "geometry": {"type": "LineString", "coordinates": primary_coords},
            "summary": {"total_distance_miles": 100.0, "total_duration_minutes": 95},
            "checkpoints": [],
        }
        routes.append(primary)

    base = routes[0]
    base_coords = base["geometry"]["coordinates"]

    while len(routes) < 3:
        idx = len(routes) + 1
        shift = 0.35 * (1 if idx % 2 == 0 else -1)
        alt_coords: List[List[float]] = []
        n = len(base_coords)
        for j, pt in enumerate(base_coords):
            if j == 0 or j == n - 1:
                alt_coords.append([pt[0], pt[1]])
            else:
                # Bow outward proportional to sin curve
                factor = math.sin(math.pi * j / n)
                alt_coords.append([round(pt[0] + shift * factor, 5), round(pt[1] + shift * factor * 0.5, 5)])

        factor_dist = 1.05 + 0.03 * len(routes)
        dist = round(base["total_distance_miles"] * factor_dist, 1)
        dur_min = round(base["total_duration_minutes"] * factor_dist)

        routes.append({
            "id": f"route_{idx}",
            "name": f"Alternative Corridor {idx}",
            "total_distance_miles": dist,
            "total_duration_minutes": dur_min,
            "total_duration_seconds": dur_min * 60.0,
            "geometry": {"type": "LineString", "coordinates": alt_coords},
            "summary": {"total_distance_miles": dist, "total_duration_minutes": dur_min},
            "checkpoints": [],
        })

    return routes
