from rest_framework import serializers

from apps.planner.models import TripPlan, TripStop
from apps.travel.serializers import build_default_destination_cover
from apps.travel.services import resolve_media_url


class TripStopSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    city = serializers.CharField(source="destination.city", read_only=True)
    cover = serializers.SerializerMethodField()

    class Meta:
        model = TripStop
        fields = ("id", "destination", "destination_name", "city", "cover", "day_number", "sequence", "note")

    def get_cover(self, obj):
        return resolve_media_url(obj.destination.cover) or build_default_destination_cover(obj.destination.name)


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
