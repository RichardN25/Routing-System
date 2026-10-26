from rest_framework import serializers

class RouteAnalysisRequestSerializer(serializers.Serializer):

    origin = serializers.CharField(
        max_length=255,
        required=True,
        allow_blank=False,
        help_text="Origin city or address string (e.g. 'Chicago, IL')",
    )
    destination = serializers.CharField(
        max_length=255,
        required=True,
        allow_blank=False,
        help_text="Destination city or address string (e.g. 'Denver, CO')",
    )
    departure_time = serializers.DateTimeField(
        required=True,
        help_text="Departure time as ISO-8601 string (e.g. '2026-10-27T08:00:00Z')",
    )
    load_weight_lbs = serializers.FloatField(
        required=True,
        min_value=0.0,
        max_value=200000.0,
        help_text="Cargo load weight in pounds (0 - 200,000 lbs)",
    )
