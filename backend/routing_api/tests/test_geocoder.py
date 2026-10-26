"""
Unit tests for Geocoding Service Integration.
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
import httpx

from routing_api.services.geocoder import GeocodingError, geocode_location


class GeocoderTests(TestCase):
    """Tests for geocode_location service using Nominatim and Mapbox."""

    def test_empty_query_raises_geocoding_error(self):
        with self.assertRaises(GeocodingError) as ctx:
            geocode_location("   ")
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_nominatim_success_chicago(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "lon": "-87.6298",
                "lat": "41.8781",
                "display_name": "Chicago, Cook County, Illinois, United States",
            }
        ]

        with patch("httpx.Client.get", return_value=mock_response):
            lon, lat, name = geocode_location("Chicago, IL")
            self.assertAlmostEqual(lon, -87.6298, places=3)
            self.assertAlmostEqual(lat, 41.8781, places=3)
            self.assertIn("Chicago", name)

    def test_nominatim_no_results_raises_geocoding_error(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch("httpx.Client.get", return_value=mock_response):
            with self.assertRaises(GeocodingError) as ctx:
                geocode_location("zzzznotaplace12345")
            self.assertIn("No coordinates found", str(ctx.exception))

    def test_nominatim_network_failure_raises_geocoding_error(self):
        with patch("httpx.Client.get", side_effect=httpx.ConnectError("Network unreachable")):
            with self.assertRaises(GeocodingError) as ctx:
                geocode_location("Chicago, IL")
            self.assertIn("Nominatim geocoding error", str(ctx.exception))

    @override_settings(MAPBOX_ACCESS_TOKEN="pk.test_mock_token")
    def test_mapbox_success(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [
                {
                    "center": [-104.9903, 39.7392],
                    "place_name": "Denver, Colorado, United States",
                }
            ]
        }

        with patch("httpx.Client.get", return_value=mock_response) as mock_get:
            lon, lat, name = geocode_location("Denver, CO")
            self.assertAlmostEqual(lon, -104.9903, places=3)
            self.assertAlmostEqual(lat, 39.7392, places=3)
            self.assertIn("Denver", name)
            # Verify Mapbox endpoint was called
            args, kwargs = mock_get.call_args
            self.assertIn("api.mapbox.com", args[0])
            self.assertEqual(kwargs["params"]["access_token"], "pk.test_mock_token")

    @override_settings(MAPBOX_ACCESS_TOKEN="pk.test_mock_token")
    def test_mapbox_no_features_raises_geocoding_error(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}

        with patch("httpx.Client.get", return_value=mock_response):
            with self.assertRaises(GeocodingError) as ctx:
                geocode_location("UnknownPlace404")
            self.assertIn("No coordinates found", str(ctx.exception))
