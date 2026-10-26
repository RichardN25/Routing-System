"""
Unit and integration tests for AnalyzeRoutesAPIView endpoint.
"""

from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AnalyzeRoutesAPITests(APITestCase):
    """Tests for POST /api/v1/routes/analyze/ endpoint."""

    def setUp(self):
        self.url = reverse("analyze-routes")
        self.valid_payload = {
            "origin": "Chicago, IL",
            "destination": "Denver, CO",
            "departure_time": "2026-10-27T08:00:00Z",
            "load_weight_lbs": 42000,
        }

    def test_missing_required_fields_returns_400(self):
        # Missing destination and load_weight_lbs
        res = self.client.post(self.url, {"origin": "Chicago, IL"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("destination", res.data)
        self.assertIn("departure_time", res.data)
        self.assertIn("load_weight_lbs", res.data)

    def test_negative_load_weight_returns_400(self):
        payload = dict(self.valid_payload)
        payload["load_weight_lbs"] = -500.0
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("load_weight_lbs", res.data)

    def test_invalid_departure_time_returns_400(self):
        payload = dict(self.valid_payload)
        payload["departure_time"] = "not-a-valid-datetime"
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("departure_time", res.data)

    @patch("routing_api.views.geocode_location")
    @patch("routing_api.views.fetch_three_routes")
    @patch("routing_api.views.fetch_weather_for_points")
    def test_valid_request_returns_200_and_expected_structure(
        self, mock_weather, mock_routes, mock_geocode
    ):
        # 1. Mock Geocoder
        mock_geocode.side_effect = [
            (-87.6298, 41.8781, "Chicago, IL"),
            (-104.9903, 39.7392, "Denver, CO"),
        ]

        # 2. Mock 3 Routes (one 1002.5 miles long haul, one 600 miles regional, one 150 miles short)
        mock_routes.return_value = [
            {
                "id": "route_1",
                "name": "I-80 W",
                "total_distance_miles": 1002.5,
                "total_duration_minutes": 910,
                "total_duration_seconds": 54600.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.6298, 41.8781], [-95.0, 41.0], [-104.9903, 39.7392]],
                },
                "summary": {"total_distance_miles": 1002.5, "total_duration_minutes": 910},
                "checkpoints": [],
            },
            {
                "id": "route_2",
                "name": "US-36 W",
                "total_distance_miles": 1050.0,
                "total_duration_minutes": 950,
                "total_duration_seconds": 57000.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.6298, 41.8781], [-94.0, 40.0], [-104.9903, 39.7392]],
                },
                "summary": {"total_distance_miles": 1050.0, "total_duration_minutes": 950},
                "checkpoints": [],
            },
            {
                "id": "route_3",
                "name": "I-70 W",
                "total_distance_miles": 1100.0,
                "total_duration_minutes": 990,
                "total_duration_seconds": 59400.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.6298, 41.8781], [-90.0, 39.0], [-104.9903, 39.7392]],
                },
                "summary": {"total_distance_miles": 1100.0, "total_duration_minutes": 990},
                "checkpoints": [],
            },
        ]

        # 3. Mock Weather API response (168-hour forecast per queried point)
        time_stamps = [
            f"2026-10-27T{h:02d}:00" if h < 24 else f"2026-10-28T{h - 24:02d}:00"
            for h in range(48)
        ] + [f"2026-10-29T{h:02d}:00" for h in range(120)]

        def side_effect_weather(points, *args, **kwargs):
            return [
                {
                    "time": time_stamps,
                    "wind_speed_10m": [20.0] * len(time_stamps),
                    "rain": [0.0] * len(time_stamps),
                    "snowfall": [0.0] * len(time_stamps),
                }
                for _ in points
            ]

        mock_weather.side_effect = side_effect_weather

        # Execute POST request
        res = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data

        # Verify top-level response contract
        self.assertIn("recommended_route_id", data)
        self.assertIn("corridor_bbox", data)
        self.assertIn("heatmap_grid", data)
        self.assertIn("routes", data)

        self.assertEqual(len(data["corridor_bbox"]), 4)
        self.assertEqual(len(data["heatmap_grid"]), 36)
        self.assertEqual(len(data["routes"]), 3)

        # Verify heatmap grid item has 49 hourly values
        sample_cell = data["heatmap_grid"][0]
        self.assertIn("coordinates", sample_cell)
        self.assertEqual(len(sample_cell["hourly_wind_mph"]), 49)
        self.assertEqual(len(sample_cell["hourly_precip_in"]), 49)

        # Verify recommended route
        recommended_id = data["recommended_route_id"]
        self.assertTrue(recommended_id.startswith("route_"))

        # Verify routes summary contains dynamically determined sample_interval_miles
        for route in data["routes"]:
            self.assertIn("sample_interval_miles", route["summary"])
            # For ~1000 mile trip (>750 mi), interval must be 50 miles
            self.assertEqual(route["summary"]["sample_interval_miles"], 50)
            self.assertIn("average_risk_score", route["summary"])
            self.assertIn("no_travel_miles", route["summary"])
            self.assertIn("checkpoints", route)
            self.assertGreater(len(route["checkpoints"]), 0)

            # Verify checkpoint structure
            first_cp = route["checkpoints"][0]
            self.assertIn("coordinates", first_cp)
            self.assertIn("eta", first_cp)
            self.assertIn("weather", first_cp)
            self.assertIn("risk_breakdown", first_cp)
            self.assertIn("overall_risk", first_cp)
            self.assertIn("risk_level_code", first_cp)
