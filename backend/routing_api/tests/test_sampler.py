"""
Unit tests for Polyline Checkpoint Sampler & ETA Calculator.
"""

from datetime import datetime, timezone
from django.test import TestCase
import geopy.distance

from routing_api.services.sampler import (
    determine_sampling_interval,
    sample_route_checkpoints,
)


class CheckpointSamplerTests(TestCase):
    """Tests for sampling interval threshold logic and checkpoint interpolation along polylines."""

    def test_determine_sampling_interval_thresholds(self):
        # Local / Short trips: <= 200 miles -> 10 miles
        self.assertEqual(determine_sampling_interval(50.0), 10)
        self.assertEqual(determine_sampling_interval(150.0), 10)
        self.assertEqual(determine_sampling_interval(200.0), 10)

        # Regional trips: 200 < miles <= 750 -> 25 miles
        self.assertEqual(determine_sampling_interval(200.1), 25)
        self.assertEqual(determine_sampling_interval(500.0), 25)
        self.assertEqual(determine_sampling_interval(750.0), 25)

        # Long haul / Cross-country: > 750 miles -> 50 miles
        self.assertEqual(determine_sampling_interval(750.1), 50)
        self.assertEqual(determine_sampling_interval(1000.0), 50)
        self.assertEqual(determine_sampling_interval(2400.0), 50)

    def _create_synthetic_line(self, distance_miles: float, num_points: int = 5):
        """Helper generating a straight-line synthetic GeoJSON LineString coordinates array."""
        start_lat = 41.8781
        start_lon = -87.6298
        start_point = geopy.Point(start_lat, start_lon)

        coords = [[start_lon, start_lat]]
        for step in range(1, num_points):
            frac = step / (num_points - 1)
            pt = geopy.distance.geodesic(miles=distance_miles * frac).destination(start_point, bearing=270)
            coords.append([round(pt.longitude, 5), round(pt.latitude, 5)])

        return coords

    def test_sample_route_110_miles_at_25_mile_interval(self):
        """
        Verifies that a 110-mile synthetic line sampled at 25-mile intervals produces
        checkpoints at 0, 25, 50, 75, 100, 110 miles with monotonically increasing ETAs.
        """
        total_dist = 110.0
        total_sec = 7200.0  # 2 hours
        dep_time = datetime(2026, 10, 27, 8, 0, 0, tzinfo=timezone.utc)
        coords = self._create_synthetic_line(total_dist, num_points=6)

        checkpoints, interval = sample_route_checkpoints(
            geojson_coords=coords,
            total_distance_miles=total_dist,
            total_duration_seconds=total_sec,
            departure_time=dep_time,
            interval_miles=25,
        )

        self.assertEqual(interval, 25)
        # Yields floor(110/25) + 2 = 4 + 2 = 6 checkpoints
        self.assertEqual(len(checkpoints), 6)

        expected_milestones = [0.0, 25.0, 50.0, 75.0, 100.0, 110.0]
        actual_milestones = [cp["mile_marker"] for cp in checkpoints]
        self.assertEqual(actual_milestones, expected_milestones)

        # Verify sum of segment_miles equals total_distance_miles within 0.01 tolerance
        sum_segment_miles = sum(cp["segment_miles"] for cp in checkpoints)
        self.assertAlmostEqual(sum_segment_miles, total_dist, places=2)

        # Verify monotonically increasing ETAs and valid ISO-8601 UTC format
        for i in range(len(checkpoints)):
            self.assertTrue(checkpoints[i]["eta"].endswith("Z"))
            if i > 0:
                prev_eta = datetime.fromisoformat(checkpoints[i - 1]["eta"].replace("Z", "+00:00"))
                curr_eta = datetime.fromisoformat(checkpoints[i]["eta"].replace("Z", "+00:00"))
                self.assertGreater(curr_eta, prev_eta)

        # Check start and end ETAs match departure and arrival times exactly
        self.assertEqual(checkpoints[0]["eta"], "2026-10-27T08:00:00Z")
        self.assertEqual(checkpoints[-1]["eta"], "2026-10-27T10:00:00Z")

    def test_sample_route_dynamic_interval_auto_selection(self):
        """
        Verifies that routes automatically select dynamic intervals based on distance.
        A 110-mile route auto-selects 10-mile interval.
        """
        total_dist = 110.0
        total_sec = 6600.0
        dep_time = datetime(2026, 10, 27, 8, 0, 0, tzinfo=timezone.utc)
        coords = self._create_synthetic_line(total_dist, num_points=6)

        checkpoints, interval = sample_route_checkpoints(
            geojson_coords=coords,
            total_distance_miles=total_dist,
            total_duration_seconds=total_sec,
            departure_time=dep_time,
            interval_miles=None,  # dynamic
        )

        # <= 200 miles auto-selects 10 miles
        self.assertEqual(interval, 10)
        expected_milestones = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0]
        actual_milestones = [cp["mile_marker"] for cp in checkpoints]
        self.assertEqual(actual_milestones, expected_milestones)

        sum_segment_miles = sum(cp["segment_miles"] for cp in checkpoints)
        self.assertAlmostEqual(sum_segment_miles, total_dist, places=2)

    def test_sample_route_long_haul_50_mile_interval(self):
        """
        Verifies long-haul trips (> 750 miles) auto-select 50-mile interval.
        """
        total_dist = 1000.0
        total_sec = 60000.0
        dep_time = datetime(2026, 10, 27, 8, 0, 0, tzinfo=timezone.utc)
        coords = self._create_synthetic_line(total_dist, num_points=10)

        checkpoints, interval = sample_route_checkpoints(
            geojson_coords=coords,
            total_distance_miles=total_dist,
            total_duration_seconds=total_sec,
            departure_time=dep_time,
            interval_miles=None,
        )

        self.assertEqual(interval, 50)
        sum_segment_miles = sum(cp["segment_miles"] for cp in checkpoints)
        self.assertAlmostEqual(sum_segment_miles, total_dist, places=2)
        self.assertEqual(checkpoints[0]["mile_marker"], 0.0)
        self.assertEqual(checkpoints[-1]["mile_marker"], 1000.0)

    def test_string_departure_time_input(self):
        """Verifies departure_time supplied as an ISO string is handled seamlessly."""
        coords = self._create_synthetic_line(50.0, num_points=4)
        checkpoints, _ = sample_route_checkpoints(
            geojson_coords=coords,
            total_distance_miles=50.0,
            total_duration_seconds=3600.0,
            departure_time="2026-10-27T08:00:00Z",
            interval_miles=10,
        )
        self.assertEqual(checkpoints[0]["eta"], "2026-10-27T08:00:00Z")
        self.assertEqual(checkpoints[-1]["eta"], "2026-10-27T09:00:00Z")
