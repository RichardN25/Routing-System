import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx


class WeatherAPIError(Exception):
    """Raised when Open-Meteo API query fails or returns invalid data."""
    pass


def generate_corridor_grid(bbox: List[float], grid_size: int = 6) -> List[Tuple[float, float]]:
    if len(bbox) < 4:
        raise ValueError("bbox must contain [min_lng, min_lat, max_lng, max_lat]")

    pad = 0.5
    min_lng = bbox[0] - pad
    min_lat = bbox[1] - pad
    max_lng = bbox[2] + pad
    max_lat = bbox[3] + pad

    grid_points: List[Tuple[float, float]] = []
    for i in range(grid_size):
        lat = min_lat + i * (max_lat - min_lat) / max(1, grid_size - 1)
        for j in range(grid_size):
            lng = min_lng + j * (max_lng - min_lng) / max(1, grid_size - 1)
            grid_points.append((round(lng, 4), round(lat, 4)))

    return grid_points


def compute_corridor_bbox(routes: List[Dict[str, Any]], pad: float = 0.5) -> List[float]:
    all_lons: List[float] = []
    all_lats: List[float] = []

    for route in routes:
        coords = route.get("geometry", {}).get("coordinates", [])
        for pt in coords:
            all_lons.append(pt[0])
            all_lats.append(pt[1])

    if not all_lons or not all_lats:
        return [-105.0, 39.0, -87.0, 42.0]

    return [
        round(min(all_lons) - pad, 4),
        round(min(all_lats) - pad, 4),
        round(max(all_lons) + pad, 4),
        round(max(all_lats) + pad, 4),
    ]


async def fetch_weather_for_points_async(
    points: List[Tuple[float, float]],
    client: Optional[httpx.AsyncClient] = None,
    batch_size: int = 50,
) -> List[Dict[str, Any]]:
    if not points:
        return []

    owns_client = client is None
    async_client = client or httpx.AsyncClient(timeout=15.0)

    try:
        # Split points into chunks of batch_size
        batches = [points[i:i + batch_size] for i in range(0, len(points), batch_size)]
        tasks = [_fetch_open_meteo_chunk(chunk, async_client) for chunk in batches]
        results_nested = await asyncio.gather(*tasks)

        # Flatten chunk results in original coordinate order
        flat_results: List[Dict[str, Any]] = []
        for chunk_res in results_nested:
            flat_results.extend(chunk_res)

        return flat_results
    finally:
        if owns_client:
            await async_client.aclose()


def fetch_weather_for_points(
    points: List[Tuple[float, float]],
    client: Optional[httpx.AsyncClient] = None,
    batch_size: int = 50,
) -> List[Dict[str, Any]]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run, fetch_weather_for_points_async(points, client, batch_size)
                ).result()
        return loop.run_until_complete(fetch_weather_for_points_async(points, client, batch_size))
    except RuntimeError:
        return asyncio.run(fetch_weather_for_points_async(points, client, batch_size))


async def _fetch_open_meteo_chunk(
    chunk: List[Tuple[float, float]],
    client: httpx.AsyncClient,
) -> List[Dict[str, Any]]:
    lats = ",".join(f"{p[1]:.4f}" for p in chunk)
    lons = ",".join(f"{p[0]:.4f}" for p in chunk)

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lats}&longitude={lons}"
        f"&hourly=wind_speed_10m,rain,snowfall"
        f"&wind_speed_unit=mph&precipitation_unit=inch"
        f"&forecast_days=7&timezone=UTC"
    )

    try:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise WeatherAPIError(f"Open-Meteo request failed: {exc}") from exc

    # If single coordinate requested, Open-Meteo returns a dict, otherwise a list of dicts
    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        raise WeatherAPIError("Unexpected response format from Open-Meteo API.")

    processed_list: List[Dict[str, Any]] = []
    for item in items:
        hourly = item.get("hourly", {})
        hourly_units = item.get("hourly_units", {})

        # Unit conversion for snowfall if returned in centimeters
        snow_unit = str(hourly_units.get("snowfall", "")).lower()
        if "cm" in snow_unit or "centimeter" in snow_unit:
            snow_vals = hourly.get("snowfall", [])
            hourly["snowfall"] = [round(float(s) * 0.393701, 2) for s in snow_vals]

        processed_list.append(hourly)

    return processed_list


def match_checkpoint_weather(checkpoint_eta: Any, hourly_data: Dict[str, Any]) -> Dict[str, float]:
    if isinstance(checkpoint_eta, str):
        dt = datetime.fromisoformat(checkpoint_eta.replace("Z", "+00:00"))
    else:
        dt = checkpoint_eta

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Round to nearest hour
    if dt.minute >= 30:
        rounded_dt = dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        rounded_dt = dt.replace(minute=0, second=0, microsecond=0)

    target_time_str = rounded_dt.strftime("%Y-%m-%dT%H:00")
    time_list = hourly_data.get("time", [])

    if target_time_str in time_list:
        idx = time_list.index(target_time_str)
    else:
        # Fallback to nearest available timestamp
        if not time_list:
            return {"wind_mph": 0.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0}
        # Clamp to bounds
        first_time = time_list[0]
        last_time = time_list[-1]
        if target_time_str < first_time:
            idx = 0
        elif target_time_str > last_time:
            idx = len(time_list) - 1
        else:
            idx = 0

    wind_list = hourly_data.get("wind_speed_10m", [])
    rain_list = hourly_data.get("rain", [])
    snow_list = hourly_data.get("snowfall", [])

    wind_mph = float(wind_list[idx]) if idx < len(wind_list) else 0.0
    rain_in_hr = float(rain_list[idx]) if idx < len(rain_list) else 0.0
    snow_in_hr = float(snow_list[idx]) if idx < len(snow_list) else 0.0

    return {
        "wind_mph": round(wind_mph, 1),
        "rain_in_hr": round(rain_in_hr, 2),
        "snow_in_hr": round(snow_in_hr, 2),
    }


def format_corridor_heatmap(
    grid_points: List[Tuple[float, float]],
    grid_weather: List[Dict[str, Any]],
    departure_time: Any,
) -> List[Dict[str, Any]]:
    if isinstance(departure_time, str):
        dep_dt = datetime.fromisoformat(departure_time.replace("Z", "+00:00"))
    else:
        dep_dt = departure_time

    if dep_dt.tzinfo is None:
        dep_dt = dep_dt.replace(tzinfo=timezone.utc)
    else:
        dep_dt = dep_dt.astimezone(timezone.utc)

    # Floor departure time to start of hour
    dep_hour_dt = dep_dt.replace(minute=0, second=0, microsecond=0)
    dep_time_str = dep_hour_dt.strftime("%Y-%m-%dT%H:00")

    heatmap_cells: List[Dict[str, Any]] = []

    for pt, weather in zip(grid_points, grid_weather):
        time_list = weather.get("time", [])
        if dep_time_str in time_list:
            start_idx = time_list.index(dep_time_str)
        else:
            start_idx = 0

        wind_all = weather.get("wind_speed_10m", [])
        rain_all = weather.get("rain", [])
        snow_all = weather.get("snowfall", [])

        # Slice 49 hours (hours 0..48 inclusive)
        hourly_wind: List[float] = []
        hourly_precip: List[float] = []
        hourly_snow: List[float] = []

        for h in range(49):
            curr_idx = start_idx + h
            if curr_idx < len(wind_all):
                w = float(wind_all[curr_idx])
            else:
                w = float(wind_all[-1]) if wind_all else 0.0

            r = float(rain_all[curr_idx]) if curr_idx < len(rain_all) else 0.0
            s = float(snow_all[curr_idx]) if curr_idx < len(snow_all) else 0.0

            hourly_wind.append(round(w, 1))
            hourly_precip.append(round(r + s, 2))
            hourly_snow.append(round(s, 2))

        heatmap_cells.append({
            "coordinates": [pt[0], pt[1]],
            "hourly_wind_mph": hourly_wind,
            "hourly_precip_in": hourly_precip,
            "hourly_snow_in": hourly_snow,
        })

    return heatmap_cells
