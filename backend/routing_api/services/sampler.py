from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import geopy.distance


def determine_sampling_interval(total_distance_miles: float) -> int:
    if total_distance_miles <= 200.0:
        return 10
    elif total_distance_miles <= 750.0:
        return 25
    else:
        return 50


def sample_route_checkpoints(
    geojson_coords: List[List[float]],
    total_distance_miles: float,
    total_duration_seconds: float,
    departure_time: Any,
    interval_miles: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    if interval_miles is None:
        interval_miles = determine_sampling_interval(total_distance_miles)

    # Parse departure_time if passed as string
    if isinstance(departure_time, str):
        # Normalize trailing Z to +00:00 for fromisoformat
        clean_time_str = departure_time.replace("Z", "+00:00")
        dep_dt = datetime.fromisoformat(clean_time_str)
    else:
        dep_dt = departure_time

    # Ensure UTC timezone awareness
    if dep_dt.tzinfo is None:
        dep_dt = dep_dt.replace(tzinfo=timezone.utc)
    else:
        dep_dt = dep_dt.astimezone(timezone.utc)

    # Handle degenerate coordinate list
    if not geojson_coords:
        return [], interval_miles

    if len(geojson_coords) == 1 or total_distance_miles <= 0.0:
        single_cp = {
            "index": 0,
            "mile_marker": 0.0,
            "segment_miles": 0.0,
            "coordinates": [round(geojson_coords[0][0], 5), round(geojson_coords[0][1], 5)],
            "eta": dep_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return [single_cp], interval_miles

    # 1. Calculate geodesic distances between consecutive vertices
    # Note: geopy expects (lat, lon), while GeoJSON provides [lon, lat]
    segment_lengths: List[float] = []
    for c1, c2 in zip(geojson_coords, geojson_coords[1:]):
        dist = geopy.distance.geodesic((c1[1], c1[0]), (c2[1], c2[0])).miles
        segment_lengths.append(dist)

    geom_total_dist = sum(segment_lengths)

    # Scaling factor to match routing API total_distance_miles with geometry
    scale_factor = (total_distance_miles / geom_total_dist) if geom_total_dist > 0 else 1.0

    # 2. Add starting checkpoint (Mile 0)
    checkpoints: List[Dict[str, Any]] = [
        {
            "index": 0,
            "mile_marker": 0.0,
            "segment_miles": 0.0,
            "coordinates": [round(geojson_coords[0][0], 5), round(geojson_coords[0][1], 5)],
            "eta": dep_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    ]

    # 3. Traverse segments and interpolate target milestones
    accumulated_miles = 0.0
    target_milestone = float(interval_miles)
    last_cp_mile = 0.0

    for i, seg_dist_geom in enumerate(segment_lengths):
        seg_dist = seg_dist_geom * scale_factor
        seg_start_dist = accumulated_miles
        seg_end_dist = accumulated_miles + seg_dist

        c1 = geojson_coords[i]
        c2 = geojson_coords[i + 1]

        # Check if one or more target milestones fall within this segment
        while target_milestone <= seg_end_dist and target_milestone < (total_distance_miles - 0.01):
            if seg_dist > 0:
                ratio = (target_milestone - seg_start_dist) / seg_dist
                ratio = max(0.0, min(1.0, ratio))
            else:
                ratio = 0.0

            # Linear interpolation of longitude and latitude
            interp_lon = c1[0] + ratio * (c2[0] - c1[0])
            interp_lat = c1[1] + ratio * (c2[1] - c1[1])

            # Elapsed duration proportional to milestone distance
            if total_distance_miles > 0:
                elapsed_sec = (target_milestone / total_distance_miles) * total_duration_seconds
            else:
                elapsed_sec = 0.0

            cp_eta = dep_dt + timedelta(seconds=elapsed_sec)
            seg_miles = target_milestone - last_cp_mile

            checkpoints.append(
                {
                    "index": len(checkpoints),
                    "mile_marker": round(target_milestone, 1),
                    "segment_miles": round(seg_miles, 2),
                    "coordinates": [round(interp_lon, 5), round(interp_lat, 5)],
                    "eta": cp_eta.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

            last_cp_mile = target_milestone
            target_milestone += float(interval_miles)

        accumulated_miles = seg_end_dist

    # 4. Append exact destination checkpoint if not already at the end
    dest_seg_miles = total_distance_miles - last_cp_mile
    if dest_seg_miles > 0.01:
        final_eta = dep_dt + timedelta(seconds=total_duration_seconds)
        dest_coords = geojson_coords[-1]
        checkpoints.append(
            {
                "index": len(checkpoints),
                "mile_marker": round(total_distance_miles, 1),
                "segment_miles": round(dest_seg_miles, 2),
                "coordinates": [round(dest_coords[0], 5), round(dest_coords[1], 5)],
                "eta": final_eta.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    else:
        # Snap the last checkpoint coordinates and milestone to exact destination
        if checkpoints:
            checkpoints[-1]["coordinates"] = [
                round(geojson_coords[-1][0], 5),
                round(geojson_coords[-1][1], 5),
            ]
            checkpoints[-1]["mile_marker"] = round(total_distance_miles, 1)

    # Normalize segment_miles sum to exactly match total_distance_miles within 0.01 tolerance
    if len(checkpoints) > 1:
        sum_prev = sum(cp["segment_miles"] for cp in checkpoints[:-1])
        checkpoints[-1]["segment_miles"] = round(total_distance_miles - sum_prev, 2)

    return checkpoints, interval_miles
