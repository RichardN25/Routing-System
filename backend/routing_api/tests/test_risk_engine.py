"""
Unit tests for Weather Risk & Load Rules Engine.
"""

from django.test import TestCase

from routing_api.services.risk_engine import (
    HIGH,
    LOW,
    MODERATE,
    NO_TRAVEL,
    SEVERE,
    aggregate_and_rank_routes,
    classify_checkpoint_risk,
)


class RiskEngineClassificationTests(TestCase):
    """Tests for checkpoint risk classification across weather and load boundaries."""

    def test_base_wind_thresholds(self):
        # Low: < 25 mph
        self.assertEqual(classify_checkpoint_risk(24.9, 0, 0, 20000)["risk_level_code"], LOW)
        # Moderate: 25 - 34 mph
        self.assertEqual(classify_checkpoint_risk(25.0, 0, 0, 20000)["risk_level_code"], MODERATE)
        self.assertEqual(classify_checkpoint_risk(34.9, 0, 0, 20000)["risk_level_code"], MODERATE)
        # High: 35 - 44 mph (standard load <= 40000)
        self.assertEqual(classify_checkpoint_risk(35.0, 0, 0, 20000)["risk_level_code"], HIGH)
        self.assertEqual(classify_checkpoint_risk(44.9, 0, 0, 20000)["risk_level_code"], HIGH)
        # Severe: 45 - 54 mph (standard load <= 30000)
        self.assertEqual(classify_checkpoint_risk(45.0, 0, 0, 20000)["risk_level_code"], SEVERE)
        self.assertEqual(classify_checkpoint_risk(54.9, 0, 0, 20000)["risk_level_code"], SEVERE)
        # No Travel: >= 55 mph
        self.assertEqual(classify_checkpoint_risk(55.0, 0, 0, 20000)["risk_level_code"], NO_TRAVEL)

    def test_base_rain_thresholds(self):
        # Low: < 0.10 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0.09, 0, 20000)["risk_level_code"], LOW)
        # Moderate: 0.10 - 0.25 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0.10, 0, 20000)["risk_level_code"], MODERATE)
        self.assertEqual(classify_checkpoint_risk(0, 0.24, 0, 20000)["risk_level_code"], MODERATE)
        # High: 0.25 - 0.50 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0.25, 0, 20000)["risk_level_code"], HIGH)
        self.assertEqual(classify_checkpoint_risk(0, 0.49, 0, 20000)["risk_level_code"], HIGH)
        # Severe: 0.50 - 1.00 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0.50, 0, 20000)["risk_level_code"], SEVERE)
        self.assertEqual(classify_checkpoint_risk(0, 1.00, 0, 20000)["risk_level_code"], SEVERE)
        # No Travel: > 1.00 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 1.01, 0, 20000)["risk_level_code"], NO_TRAVEL)

    def test_base_snow_thresholds(self):
        # Low: < 0.5 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0, 0.49, 20000)["risk_level_code"], LOW)
        # Moderate: 0.5 - 1.0 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0, 0.5, 20000)["risk_level_code"], MODERATE)
        self.assertEqual(classify_checkpoint_risk(0, 0, 0.99, 20000)["risk_level_code"], MODERATE)
        # High: 1.0 - 2.0 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0, 1.0, 20000)["risk_level_code"], HIGH)
        self.assertEqual(classify_checkpoint_risk(0, 0, 1.99, 20000)["risk_level_code"], HIGH)
        # Severe: 2.0 - 3.0 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0, 2.0, 20000)["risk_level_code"], SEVERE)
        self.assertEqual(classify_checkpoint_risk(0, 0, 3.0, 20000)["risk_level_code"], SEVERE)
        # No Travel: > 3.0 in/hr
        self.assertEqual(classify_checkpoint_risk(0, 0, 3.01, 20000)["risk_level_code"], NO_TRAVEL)

    def test_load_weight_rule_1_wind_ge_55(self):
        # Wind >= 55 mph -> No Travel for any load weight
        res_empty = classify_checkpoint_risk(55.0, 0, 0, 15000)
        self.assertEqual(res_empty["risk_level_code"], NO_TRAVEL)
        self.assertEqual(res_empty["overall_risk"], "No Travel")
        self.assertIn(">= 55 mph", res_empty["triggered_load_rule"])

        res_heavy = classify_checkpoint_risk(58.0, 0, 0, 45000)
        self.assertEqual(res_heavy["risk_level_code"], NO_TRAVEL)

    def test_load_weight_rule_2_wind_45_to_54_boundary(self):
        # 45 mph wind with 30,000 lb load returns Severe (3)
        res_at_limit = classify_checkpoint_risk(45.0, 0, 0, 30000)
        self.assertEqual(res_at_limit["risk_level_code"], SEVERE)
        self.assertEqual(res_at_limit["overall_risk"], "Severe")
        self.assertIsNone(res_at_limit["triggered_load_rule"])

        # 45 mph wind with 30,001 lb load escalates to No Travel (4)
        res_over_limit = classify_checkpoint_risk(45.0, 0, 0, 30001)
        self.assertEqual(res_over_limit["risk_level_code"], NO_TRAVEL)
        self.assertEqual(res_over_limit["overall_risk"], "No Travel")
        self.assertIn(">30,000 lb", res_over_limit["triggered_load_rule"])

    def test_load_weight_rule_3_wind_35_to_44_boundary(self):
        # 35 mph wind with 40,000 lb load returns High (2)
        res_at_limit = classify_checkpoint_risk(35.0, 0, 0, 40000)
        self.assertEqual(res_at_limit["risk_level_code"], HIGH)
        self.assertEqual(res_at_limit["overall_risk"], "High")
        self.assertIsNone(res_at_limit["triggered_load_rule"])

        # 35 mph wind with 40,001 lb load escalates to Severe (3)
        res_over_limit = classify_checkpoint_risk(35.0, 0, 0, 40001)
        self.assertEqual(res_over_limit["risk_level_code"], SEVERE)
        self.assertEqual(res_over_limit["overall_risk"], "Severe")
        self.assertIn(">40,000 lb", res_over_limit["triggered_load_rule"])

    def test_overall_risk_is_max_of_conditions(self):
        # Wind is Moderate (1), Rain is Severe (3), Snow is Low (0)
        res = classify_checkpoint_risk(28.0, 0.75, 0.0, 20000)
        self.assertEqual(res["risk_level_code"], SEVERE)
        self.assertEqual(res["risk_breakdown"]["wind"], "Moderate")
        self.assertEqual(res["risk_breakdown"]["rain"], "Severe")
        self.assertEqual(res["risk_breakdown"]["snow"], "Low")
        self.assertEqual(res["overall_risk"], "Severe")


class RiskEngineAggregationAndRankingTests(TestCase):
    """Tests for route summary aggregation and tie-breaker sorting order."""

    def test_route_sorting_prioritizes_fewest_no_travel_miles(self):
        # Route A has 10 no-travel miles but very short travel time (300 min)
        route_a = {
            "id": "route_a",
            "summary": {"total_distance_miles": 500.0, "total_duration_minutes": 300},
            "checkpoints": [
                {"segment_miles": 10.0, "risk_level_code": NO_TRAVEL},
                {"segment_miles": 490.0, "risk_level_code": LOW},
            ],
        }
        # Route B has 0 no-travel miles, 50 severe miles, and longer travel time (450 min)
        route_b = {
            "id": "route_b",
            "summary": {"total_distance_miles": 500.0, "total_duration_minutes": 450},
            "checkpoints": [
                {"segment_miles": 50.0, "risk_level_code": SEVERE},
                {"segment_miles": 450.0, "risk_level_code": LOW},
            ],
        }

        ranked = aggregate_and_rank_routes([route_a, route_b])
        # Route B must rank first because it avoids No Travel miles
        self.assertEqual(ranked[0]["id"], "route_b")
        self.assertTrue(ranked[0]["is_recommended"])
        self.assertFalse(ranked[1]["is_recommended"])
        self.assertTrue(route_a["has_no_travel_warning"])
        self.assertFalse(route_b["has_no_travel_warning"])

    def test_route_sorting_prioritizes_fewest_severe_miles(self):
        # Both routes have 0 no-travel miles
        route_a = {
            "id": "route_a",
            "summary": {"total_distance_miles": 400.0, "total_duration_minutes": 250},
            "checkpoints": [
                {"segment_miles": 30.0, "risk_level_code": SEVERE},
                {"segment_miles": 370.0, "risk_level_code": LOW},
            ],
        }
        route_b = {
            "id": "route_b",
            "summary": {"total_distance_miles": 400.0, "total_duration_minutes": 260},
            "checkpoints": [
                {"segment_miles": 10.0, "risk_level_code": SEVERE},
                {"segment_miles": 50.0, "risk_level_code": HIGH},
                {"segment_miles": 340.0, "risk_level_code": LOW},
            ],
        }

        ranked = aggregate_and_rank_routes([route_a, route_b])
        # Route B has only 10 severe miles vs Route A's 30
        self.assertEqual(ranked[0]["id"], "route_b")

    def test_route_sorting_prioritizes_fewest_high_miles(self):
        # Both have 0 no-travel and 0 severe miles
        route_a = {
            "id": "route_a",
            "summary": {"total_distance_miles": 300.0, "total_duration_minutes": 180},
            "checkpoints": [
                {"segment_miles": 50.0, "risk_level_code": HIGH},
                {"segment_miles": 250.0, "risk_level_code": LOW},
            ],
        }
        route_b = {
            "id": "route_b",
            "summary": {"total_distance_miles": 300.0, "total_duration_minutes": 190},
            "checkpoints": [
                {"segment_miles": 25.0, "risk_level_code": HIGH},
                {"segment_miles": 275.0, "risk_level_code": LOW},
            ],
        }

        ranked = aggregate_and_rank_routes([route_a, route_b])
        self.assertEqual(ranked[0]["id"], "route_b")

    def test_route_sorting_prioritizes_lowest_average_risk_score(self):
        # Both have 0 no-travel, 0 severe, and 50 high miles
        # Route A has 100 moderate miles
        route_a = {
            "id": "route_a",
            "summary": {"total_distance_miles": 500.0, "total_duration_minutes": 300},
            "checkpoints": [
                {"segment_miles": 50.0, "risk_level_code": HIGH},
                {"segment_miles": 100.0, "risk_level_code": MODERATE},
                {"segment_miles": 350.0, "risk_level_code": LOW},
            ],
        }
        # Route B has 0 moderate miles (lower average risk)
        route_b = {
            "id": "route_b",
            "summary": {"total_distance_miles": 500.0, "total_duration_minutes": 310},
            "checkpoints": [
                {"segment_miles": 50.0, "risk_level_code": HIGH},
                {"segment_miles": 450.0, "risk_level_code": LOW},
            ],
        }

        ranked = aggregate_and_rank_routes([route_a, route_b])
        self.assertEqual(ranked[0]["id"], "route_b")
        self.assertLess(
            ranked[0]["summary"]["average_risk_score"],
            ranked[1]["summary"]["average_risk_score"],
        )

    def test_route_sorting_tie_breaker_shortest_travel_time(self):
        # Identical risk profiles, different duration
        route_a = {
            "id": "route_a",
            "summary": {"total_distance_miles": 200.0, "total_duration_minutes": 150},
            "checkpoints": [{"segment_miles": 200.0, "risk_level_code": LOW}],
        }
        route_b = {
            "id": "route_b",
            "summary": {"total_distance_miles": 200.0, "total_duration_minutes": 130},
            "checkpoints": [{"segment_miles": 200.0, "risk_level_code": LOW}],
        }

        ranked = aggregate_and_rank_routes([route_a, route_b])
        self.assertEqual(ranked[0]["id"], "route_b")
        self.assertEqual(ranked[0]["summary"]["total_duration_minutes"], 130)
