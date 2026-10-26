import os
from typing import Optional, Tuple
from django.conf import settings
import httpx


class GeocodingError(Exception):
    """Raised when geocoding a location string fails or returns no results."""
    pass


def geocode_location(
    query: str,
    client: Optional[httpx.Client] = None,
) -> Tuple[float, float, str]:
    clean_query = query.strip()
    if not clean_query:
        raise GeocodingError("Geocoding query cannot be empty.")

    mapbox_token = getattr(settings, "MAPBOX_ACCESS_TOKEN", None) or os.getenv("MAPBOX_ACCESS_TOKEN", "").strip()

    owns_client = client is None
    http_client = client or httpx.Client(timeout=10.0)

    try:
        if mapbox_token:
            return _geocode_mapbox(clean_query, mapbox_token, http_client)
        else:
            return _geocode_nominatim(clean_query, http_client)
    finally:
        if owns_client:
            http_client.close()


def _geocode_mapbox(
    query: str,
    token: str,
    client: httpx.Client,
) -> Tuple[float, float, str]:
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"
    params = {
        "access_token": token,
        "limit": 1,
    }
    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise GeocodingError(f"Mapbox geocoding error for '{query}': {exc}") from exc

    features = data.get("features", [])
    if not features:
        raise GeocodingError(f"No coordinates found for location: '{query}'.")

    feature = features[0]
    center = feature.get("center")  # [lon, lat]
    if not center or len(center) < 2:
        raise GeocodingError(f"Invalid coordinate data in Mapbox response for '{query}'.")

    lon = float(center[0])
    lat = float(center[1])
    place_name = feature.get("place_name", query)
    return lon, lat, place_name


def _geocode_nominatim(
    query: str,
    client: httpx.Client,
) -> Tuple[float, float, str]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
    }
    headers = {
        "User-Agent": "WeatherAwareTruckRouting/1.0 (contact: dispatch@weather-truck-routing.local)",
    }
    try:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise GeocodingError(f"Nominatim geocoding error for '{query}': {exc}") from exc

    if not data or not isinstance(data, list):
        raise GeocodingError(f"No coordinates found for location: '{query}'.")

    first = data[0]
    try:
        lon = float(first["lon"])
        lat = float(first["lat"])
        place_name = first.get("display_name", query)
    except (KeyError, ValueError) as exc:
        raise GeocodingError(f"Malformed coordinate data in Nominatim response for '{query}': {exc}") from exc

    return lon, lat, place_name
