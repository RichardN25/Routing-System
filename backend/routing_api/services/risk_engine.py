from typing import Any, Dict, List, Optional

# Severity integer codes
LOW = 0
MODERATE = 1
HIGH = 2
SEVERE = 3
NO_TRAVEL = 4

# Severity human-readable labels
RISK_LABELS: Dict[int, str] = {
    LOW: "Low",
    MODERATE: "Moderate",
    HIGH: "High",
    SEVERE: "Severe",
    NO_TRAVEL: "No Travel",
}


def classify_checkpoint_risk(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_weight_lbs: float,
) -> Dict[str, Any]:
    # 1. Base Wind Risk
    if wind_mph >= 55.0:
        wind_risk = NO_TRAVEL
    elif wind_mph >= 45.0:
        wind_risk = SEVERE
    elif wind_mph >= 35.0:
        wind_risk = HIGH
    elif wind_mph >= 25.0:
        wind_risk = MODERATE
    else:
        wind_risk = LOW

    # 2. Apply Commercial Load Rules to Wind Risk
    triggered_load_rule: Optional[str] = None
    if wind_mph >= 55.0:
        wind_risk = NO_TRAVEL
        triggered_load_rule = "Wind >= 55 mph (No Travel for any load)"
    elif 45.0 <= wind_mph < 55.0 and load_weight_lbs > 30000.0:
        wind_risk = NO_TRAVEL
        triggered_load_rule = "45–54 mph wind + >30,000 lb load (No Travel)"
    elif 35.0 <= wind_mph < 45.0 and load_weight_lbs > 40000.0:
        wind_risk = max(wind_risk, SEVERE)
        triggered_load_rule = "35–44 mph wind + >40,000 lb load (Severe)"

    # 3. Base Rain Risk
    if rain_in_hr > 1.00:
        rain_risk = NO_TRAVEL
    elif rain_in_hr >= 0.50:
        rain_risk = SEVERE
    elif rain_in_hr >= 0.25:
        rain_risk = HIGH
    elif rain_in_hr >= 0.10:
        rain_risk = MODERATE
    else:
        rain_risk = LOW

    # 4. Base Snow Risk
    if snow_in_hr > 3.0:
        snow_risk = NO_TRAVEL
    elif snow_in_hr >= 2.0:
        snow_risk = SEVERE
    elif snow_in_hr >= 1.0:
        snow_risk = HIGH
    elif snow_in_hr >= 0.5:
        snow_risk = MODERATE
    else:
        snow_risk = LOW

    # 5. Overall Checkpoint Risk
    overall_risk_code = max(wind_risk, rain_risk, snow_risk)

    return {
        "risk_breakdown": {
            "wind": RISK_LABELS[wind_risk],
            "rain": RISK_LABELS[rain_risk],
            "snow": RISK_LABELS[snow_risk],
        },
        "wind_risk_code": wind_risk,
        "rain_risk_code": rain_risk,
        "snow_risk_code": snow_risk,
        "overall_risk": RISK_LABELS[overall_risk_code],
        "risk_level_code": overall_risk_code,
        "triggered_load_rule": triggered_load_rule,
    }


def aggregate_and_rank_routes(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for route in routes:
        checkpoints = route.get("checkpoints", [])
        no_travel_miles = 0.0
        severe_miles = 0.0
        high_miles = 0.0
        moderate_miles = 0.0
        low_miles = 0.0
        weighted_risk_sum = 0.0
        total_calc_dist = 0.0

        for cp in checkpoints:
            segment_len = float(cp.get("segment_miles", 0.0))
            code = int(cp.get("risk_level_code", cp.get("risk_code", LOW)))

            if code == NO_TRAVEL:
                no_travel_miles += segment_len
            elif code == SEVERE:
                severe_miles += segment_len
            elif code == HIGH:
                high_miles += segment_len
            elif code == MODERATE:
                moderate_miles += segment_len
            else:
                low_miles += segment_len

            weighted_risk_sum += code * segment_len
            total_calc_dist += segment_len

        # Determine total route distance
        summary = route.setdefault("summary", {})
        total_distance = float(summary.get("total_distance_miles") or total_calc_dist)

        if total_distance > 0:
            avg_risk = weighted_risk_sum / total_distance
        else:
            avg_risk = 0.0

        summary["no_travel_miles"] = round(no_travel_miles, 1)
        summary["severe_miles"] = round(severe_miles, 1)
        summary["high_miles"] = round(high_miles, 1)
        summary["moderate_miles"] = round(moderate_miles, 1)
        summary["low_miles"] = round(low_miles, 1)
        summary["average_risk_score"] = round(avg_risk, 2)

        route["has_no_travel_warning"] = (summary["no_travel_miles"] > 0)

    # Sort routes based on specification tie-breaker hierarchy
    routes.sort(
        key=lambda r: (
            r.get("summary", {}).get("no_travel_miles", 0.0),
            r.get("summary", {}).get("severe_miles", 0.0),
            r.get("summary", {}).get("high_miles", 0.0),
            round(r.get("summary", {}).get("average_risk_score", 0.0), 3),
            r.get("summary", {}).get("total_duration_minutes", 0),
        )
    )

    # Assign recommendation badges and descriptive reasons
    for i, route in enumerate(routes):
        if i == 0:
            route["is_recommended"] = True
            summary = route.get("summary", {})
            if summary.get("no_travel_miles", 0.0) > 0:
                route["recommendation_reason"] = (
                    "Warning: All available routes encounter impassable weather conditions. "
                    "Selected path with least severe exposure."
                )
            elif summary.get("severe_miles", 0.0) == 0 and summary.get("high_miles", 0.0) == 0:
                route["recommendation_reason"] = (
                    "Fewest severe weather miles and lowest overall risk"
                )
            elif summary.get("severe_miles", 0.0) == 0:
                route["recommendation_reason"] = (
                    "Safest corridor avoiding all severe weather segments"
                )
            else:
                route["recommendation_reason"] = (
                    "Fewest severe weather miles and lowest overall risk"
                )
        else:
            route["is_recommended"] = False
            route["recommendation_reason"] = None

    return routes
