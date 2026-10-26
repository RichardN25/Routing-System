from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing_api.serializers import RouteAnalysisRequestSerializer
from routing_api.services.geocoder import GeocodingError, geocode_location
from routing_api.services.risk_engine import (
    aggregate_and_rank_routes,
    classify_checkpoint_risk,
)
from routing_api.services.router import RoutingError, fetch_three_routes
from routing_api.services.sampler import sample_route_checkpoints
from routing_api.services.weather import (
    WeatherAPIError,
    compute_corridor_bbox,
    fetch_weather_for_points,
    format_corridor_heatmap,
    generate_corridor_grid,
    match_checkpoint_weather,
)


class AnalyzeRoutesAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = RouteAnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        origin_query = serializer.validated_data["origin"]
        dest_query = serializer.validated_data["destination"]
        departure_time = serializer.validated_data["departure_time"]
        load_weight_lbs = serializer.validated_data["load_weight_lbs"]

        # 1. Geocode origin and destination
        try:
            origin_lon, origin_lat, _ = geocode_location(origin_query)
        except GeocodingError as exc:
            return Response(
                {"error": f"Failed to geocode origin '{origin_query}': {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dest_lon, dest_lat, _ = geocode_location(dest_query)
        except GeocodingError as exc:
            return Response(
                {"error": f"Failed to geocode destination '{dest_query}': {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Fetch 3 alternative routes
        try:
            routes = fetch_three_routes((origin_lon, origin_lat), (dest_lon, dest_lat))
        except RoutingError as exc:
            return Response(
                {"error": f"Routing service failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            return Response(
                {"error": f"Unexpected error during route generation: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 3. Sample checkpoints for each route
        all_checkpoint_coords = []
        for route in routes:
            checkpoints, interval_miles = sample_route_checkpoints(
                geojson_coords=route["geometry"]["coordinates"],
                total_distance_miles=route["total_distance_miles"],
                total_duration_seconds=route["total_duration_seconds"],
                departure_time=departure_time,
            )
            route["checkpoints"] = checkpoints
            route["summary"]["sample_interval_miles"] = interval_miles
            if checkpoints:
                route["summary"]["eta"] = checkpoints[-1]["eta"]
            else:
                route["summary"]["eta"] = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            for cp in checkpoints:
                all_checkpoint_coords.append(tuple(cp["coordinates"]))

        # 4. Generate corridor bounding box & 6x6 heatmap grid
        bbox = compute_corridor_bbox(routes, pad=0.5)
        grid_points = generate_corridor_grid(bbox, grid_size=6)

        # 5. Batch-fetch weather forecasts for all checkpoints + corridor grid points
        all_query_points = all_checkpoint_coords + grid_points
        try:
            all_weather = fetch_weather_for_points(all_query_points, batch_size=50)
        except WeatherAPIError as exc:
            return Response(
                {"error": f"Weather service failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            return Response(
                {"error": f"Unexpected error fetching weather: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        num_checkpoints = len(all_checkpoint_coords)
        checkpoint_weather_results = all_weather[:num_checkpoints]
        grid_weather_results = all_weather[num_checkpoints:]

        # 6. Match weather to checkpoints and classify risks
        w_idx = 0
        for route in routes:
            for cp in route["checkpoints"]:
                hourly = checkpoint_weather_results[w_idx] if w_idx < len(checkpoint_weather_results) else {}
                w_idx += 1

                weather_data = match_checkpoint_weather(cp["eta"], hourly)
                cp["weather"] = weather_data

                risk_data = classify_checkpoint_risk(
                    wind_mph=weather_data["wind_mph"],
                    rain_in_hr=weather_data["rain_in_hr"],
                    snow_in_hr=weather_data["snow_in_hr"],
                    load_weight_lbs=load_weight_lbs,
                )
                cp["risk_breakdown"] = risk_data["risk_breakdown"]
                cp["overall_risk"] = risk_data["overall_risk"]
                cp["risk_level_code"] = risk_data["risk_level_code"]
                cp["triggered_load_rule"] = risk_data["triggered_load_rule"]

        # 7. Aggregate risk mileage summaries and rank routes
        ranked_routes = aggregate_and_rank_routes(routes)
        recommended_id = ranked_routes[0]["id"] if ranked_routes else ""

        # 8. Format corridor heatmap grid
        heatmap_grid = format_corridor_heatmap(grid_points, grid_weather_results, departure_time)

        return Response(
            {
                "recommended_route_id": recommended_id,
                "corridor_bbox": bbox,
                "heatmap_grid": heatmap_grid,
                "routes": ranked_routes,
            },
            status=status.HTTP_200_OK,
        )
