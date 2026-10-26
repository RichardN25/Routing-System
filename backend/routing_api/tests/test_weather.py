"""
Unit tests for Async Batch Weather & Corridor Grid Service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from django.test import TestCase
import httpx

from routing_api.services.weather import (
    WeatherAPIError,
    compute_corridor_bbox,
    fetch_weather_for_points,
    format_corridor_heatmap,
    generate_corridor_grid,
    match_checkpoint_weather,
)


class WeatherServiceTests(TestCase):
    """Tests for corridor grid generation, checkpoint matching, and batch weather fetching."""

    def setUp(self):
        # 7-day hourly timestamps (168 hours) starting from 2026-10-27 00:00 UTC
        self.time_stamps = [
            f"2026-10-27T{h:02d}:00" if h < 24 else f"2026-10-28T{h - 24:02d}:00"
            for h in range(48)
        ] + [f"2026-10-29T{h:02d}:00" for h in range(24)]
        # Extend to 168 hours
        while len(self.time_stamps) < 168:
            self.time_stamps.append(f"2026-10-30T00:00")

        self.mock_hourly = {
            "time": self.time_stamps,
            "wind_speed_10m": [10.0 + (i % 20) for i in range(168)],
            "rain": [0.05 * (i % 5) for i in range(168)],
            "snowfall": [0.0 for _ in range(168)],
        }

    def test_generate_corridor_grid_dimensions_and_padding(self):
        bbox = [-105.0, 39.5, -87.6, 42.0]
        grid = generate_corridor_grid(bbox, grid_size=6)

        # 6 x 6 = 36 points
        self.assertEqual(len(grid), 36)

        lons = [p[0] for p in grid]
        lats = [p[1] for p in grid]

        # Padded by 0.5 degrees
        self.assertAlmostEqual(min(lons), -105.5, places=2)
        self.assertAlmostEqual(max(lons), -87.1, places=2)
        self.assertAlmostEqual(min(lats), 39.0, places=2)
        self.assertAlmostEqual(max(lats), 42.5, places=2)

    def test_compute_corridor_bbox_from_routes(self):
        routes = [
            {
                "geometry": {
                    "coordinates": [[-100.0, 40.0], [-90.0, 42.0]],
                }
            }
        ]
        bbox = compute_corridor_bbox(routes, pad=0.5)
        # Expected: min_lng - pad, min_lat - pad, max_lng + pad, max_lat + pad
        self.assertEqual(bbox, [-100.5, 39.5, -89.5, 42.5])

    def test_match_checkpoint_weather_rounds_to_nearest_hour(self):
        # 08:15 UTC -> rounds to 08:00 UTC
        eta_1 = datetime(2026, 10, 27, 8, 15, tzinfo=timezone.utc)
        w1 = match_checkpoint_weather(eta_1, self.mock_hourly)
        idx_08 = self.time_stamps.index("2026-10-27T08:00")
        self.assertEqual(w1["wind_mph"], self.mock_hourly["wind_speed_10m"][idx_08])
        self.assertAlmostEqual(w1["rain_in_hr"], self.mock_hourly["rain"][idx_08], places=2)

        # 08:45 UTC -> rounds to 09:00 UTC
        eta_2 = datetime(2026, 10, 27, 8, 45, tzinfo=timezone.utc)
        w2 = match_checkpoint_weather(eta_2, self.mock_hourly)
        idx_09 = self.time_stamps.index("2026-10-27T09:00")
        self.assertEqual(w2["wind_mph"], self.mock_hourly["wind_speed_10m"][idx_09])

    def test_match_checkpoint_weather_matches_checkpoint_eta_not_departure(self):
        # ETA is 14:00 (6 hours after departure at 08:00)
        eta_later = "2026-10-27T14:00:00Z"
        w_later = match_checkpoint_weather(eta_later, self.mock_hourly)
        idx_14 = self.time_stamps.index("2026-10-27T14:00")
        self.assertEqual(w_later["wind_mph"], self.mock_hourly["wind_speed_10m"][idx_14])

    def test_format_corridor_heatmap_returns_49_hourly_values(self):
        grid_points = [(-95.0, 41.0), (-94.0, 41.5)]
        grid_weather = [self.mock_hourly, self.mock_hourly]
        departure = datetime(2026, 10, 27, 8, 0, tzinfo=timezone.utc)

        cells = format_corridor_heatmap(grid_points, grid_weather, departure)
        self.assertEqual(len(cells), 2)

        for cell in cells:
            self.assertIn("coordinates", cell)
            self.assertEqual(len(cell["hourly_wind_mph"]), 49)
            self.assertEqual(len(cell["hourly_precip_in"]), 49)
            # Verify index 0 matches 08:00 departure
            idx_start = self.time_stamps.index("2026-10-27T08:00")
            self.assertEqual(cell["hourly_wind_mph"][0], self.mock_hourly["wind_speed_10m"][idx_start])

    def test_fetch_weather_for_points_chunks_batches(self):
        # Generate 150 checkpoints + 36 grid points = 186 points
        test_points = [(-90.0 + (i * 0.05), 40.0 + (i * 0.02)) for i in range(186)]

        # Mock Open-Meteo response returning chunk items
        def mock_chunk_response(url, *args, **kwargs):
            # Parse latitude query to see how many points requested
            import urllib.parse
            parsed = urllib.parse.urlparse(str(url))
            qs = urllib.parse.parse_qs(parsed.query)
            lats = qs.get("latitude", [""])[0].split(",")
            count = len(lats)

            items = [
                {
                    "hourly": self.mock_hourly,
                    "hourly_units": {"snowfall": "inch"},
                }
                for _ in range(count)
            ]
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = items if count > 1 else items[0]
            return resp

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = mock_chunk_response
            results = fetch_weather_for_points(test_points, batch_size=50)

            # 186 points with batch size 50 -> ceil(186/50) = 4 HTTP calls
            self.assertEqual(mock_get.call_count, 4)
            self.assertEqual(len(results), 186)

    def test_snowfall_unit_conversion_from_cm_to_inch(self):
        test_points = [(-87.62, 41.87)]
        cm_snow_hourly = {
            "time": ["2026-10-27T08:00"],
            "wind_speed_10m": [15.0],
            "rain": [0.0],
            "snowfall": [10.0],  # 10 cm
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "hourly": cm_snow_hourly,
            "hourly_units": {"snowfall": "cm"},
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            results = fetch_weather_for_points(test_points)
            self.assertEqual(len(results), 1)
            # 10 cm * 0.393701 = 3.94 inches
            self.assertAlmostEqual(results[0]["snowfall"][0], 3.94, places=2)
