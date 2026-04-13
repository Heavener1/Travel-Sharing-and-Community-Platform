from rest_framework import serializers

from apps.planner.models import TripPlan, TripStop


class TripStopSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    city = serializers.CharField(source="destination.city", read_only=True)
    cover = serializers.CharField(source="destination.cover", read_only=True)

    class Meta:
        model = TripStop
        fields = ("id", "destination", "destination_name", "city", "cover", "day_number", "sequence", "note")


class TripPlanSerializer(serializers.ModelSerializer):
    stops = TripStopSerializer(many=True, read_only=True)

    class Meta:
        model = TripPlan
        fields = (
            "id",
            "title",
            "departure_city",
            "destination_city",
            "days",
            "budget",
            "preferences",
            "created_at",
            "stops",
        )
