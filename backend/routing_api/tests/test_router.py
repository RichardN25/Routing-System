"""
Unit tests for 3-Route Generation Service & Waypoint Fallback.
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase
import httpx

from routing_api.services.router import RoutingError, fetch_three_routes


class RouterTests(TestCase):
    """Tests for fetch_three_routes service and waypoint fallback mechanism."""

    def setUp(self):
        self.chicago = (-87.6298, 41.8781)
        self.denver = (-104.9903, 39.7392)

    def test_identical_origin_dest_raises_routing_error(self):
        with self.assertRaises(RoutingError) as ctx:
            fetch_three_routes(self.chicago, self.chicago)
        self.assertIn("cannot be identical", str(ctx.exception))

    def test_fetch_three_routes_when_api_returns_three_alternatives(self):
        """Verifies parsing when OSRM/Mapbox returns 3 natural alternative routes."""
        mock_raw_routes = [
            {
                "distance": 1613000,  # ~1002.3 miles
                "duration": 54600,  # ~910 minutes
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.6298, 41.8781], [-95.0, 41.5], [-104.9903, 39.7392]],
                },
                "legs": [{"steps": [{"ref": "I-80 W", "name": "Interstate 80"}]}],
            },
            {
                "distance": 1650000,
                "duration": 56000,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.6298, 41.8781], [-93.5, 40.0], [-104.9903, 39.7392]],
                },
                "legs": [{"steps": [{"ref": "US-36 W", "name": "US Highway 36"}]}],
            },
            {
                "distance": 1700000,
                "duration": 58000,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.6298, 41.8781], [-90.0, 39.0], [-104.9903, 39.7392]],
                },
                "legs": [{"steps": [{"ref": "I-70 W", "name": "Interstate 70"}]}],
            },
        ]

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": "Ok", "routes": mock_raw_routes}

        with patch("httpx.Client.get", return_value=mock_resp):
            routes = fetch_three_routes(self.chicago, self.denver)

            self.assertEqual(len(routes), 3)
            self.assertEqual(routes[0]["id"], "route_1")
            self.assertEqual(routes[1]["id"], "route_2")
            self.assertEqual(routes[2]["id"], "route_3")

            self.assertEqual(routes[0]["name"], "I-80 W")
            self.assertEqual(routes[1]["name"], "US-36 W")
            self.assertEqual(routes[2]["name"], "I-70 W")

            for r in routes:
                self.assertGreater(r["total_distance_miles"], 900.0)
                self.assertGreater(r["total_duration_minutes"], 800)
                self.assertEqual(r["geometry"]["type"], "LineString")
                self.assertGreaterEqual(len(r["geometry"]["coordinates"]), 2)

    def test_fetch_three_routes_triggers_waypoint_fallback_when_fewer_than_three(self):
        """Verifies waypoint fallback is triggered when API returns only 1 route."""
        primary_raw = {
            "distance": 1613000,
            "duration": 54600,
            "geometry": {
                "type": "LineString",
                "coordinates": [[-87.6298, 41.8781], [-95.0, 41.5], [-104.9903, 39.7392]],
            },
            "legs": [{"steps": [{"ref": "I-80 W"}]}],
        }

        # Mock initial call returning 1 route, subsequent waypoint calls returning fallback routes
        fallback_raw_1 = {
            "distance": 1680000,
            "duration": 57000,
            "geometry": {
                "type": "LineString",
                "coordinates": [[-87.6298, 41.8781], [-96.0, 42.0], [-104.9903, 39.7392]],
            },
            "legs": [{"steps": [{"ref": "I-90 W"}]}],
        }
        fallback_raw_2 = {
            "distance": 1720000,
            "duration": 59000,
            "geometry": {
                "type": "LineString",
                "coordinates": [[-87.6298, 41.8781], [-94.0, 39.5], [-104.9903, 39.7392]],
            },
            "legs": [{"steps": [{"ref": "I-70 W"}]}],
        }

        resp_init = MagicMock(spec=httpx.Response)
        resp_init.status_code = 200
        resp_init.json.return_value = {"code": "Ok", "routes": [primary_raw]}

        resp_wp1 = MagicMock(spec=httpx.Response)
        resp_wp1.status_code = 200
        resp_wp1.json.return_value = {"code": "Ok", "routes": [fallback_raw_1]}

        resp_wp2 = MagicMock(spec=httpx.Response)
        resp_wp2.status_code = 200
        resp_wp2.json.return_value = {"code": "Ok", "routes": [fallback_raw_2]}

        with patch("httpx.Client.get", side_effect=[resp_init, resp_wp1, resp_wp2]):
            routes = fetch_three_routes(self.chicago, self.denver)

            self.assertEqual(len(routes), 3)
            self.assertEqual(routes[0]["id"], "route_1")
            self.assertEqual(routes[1]["id"], "route_2")
            self.assertEqual(routes[2]["id"], "route_3")
            self.assertEqual(routes[0]["name"], "I-80 W")
            self.assertEqual(routes[1]["name"], "I-90 W")
            self.assertEqual(routes[2]["name"], "I-70 W")

    def test_synthesizes_routes_if_external_service_completely_offline(self):
        """Verifies that if external routing returns 1 route and waypoints fail, 3 valid routes are synthesized."""
        primary_raw = {
            "distance": 1600000,
            "duration": 54000,
            "geometry": {
                "type": "LineString",
                "coordinates": [[-87.6298, 41.8781], [-95.0, 41.0], [-104.9903, 39.7392]],
            },
            "legs": [{"steps": [{"ref": "I-80"}]}],
        }

        resp_init = MagicMock(spec=httpx.Response)
        resp_init.status_code = 200
        resp_init.json.return_value = {"code": "Ok", "routes": [primary_raw]}

        # Subsequent waypoint requests return error
        resp_err = MagicMock(spec=httpx.Response)
        resp_err.status_code = 500
        resp_err.side_effect = httpx.RequestError("Waypoint routing failed")

        with patch("httpx.Client.get", side_effect=[resp_init, resp_err, resp_err, resp_err, resp_err]):
            routes = fetch_three_routes(self.chicago, self.denver)
            self.assertEqual(len(routes), 3)
            for r in routes:
                self.assertEqual(r["geometry"]["type"], "LineString")
                self.assertGreater(len(r["geometry"]["coordinates"]), 1)
                self.assertGreater(r["total_distance_miles"], 0.0)
