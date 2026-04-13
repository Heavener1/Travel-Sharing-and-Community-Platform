from collections import defaultdict

from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.planner.models import TripPlan, TripStop
from apps.planner.serializers import TripPlanSerializer
from apps.social.models import UserAction
from apps.travel.models import Destination


class TripPlanListCreateView(generics.ListCreateAPIView):
    serializer_class = TripPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TripPlan.objects.filter(user=self.request.user).prefetch_related("stops__destination")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TripGeneratorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        departure_city = (request.data.get("departure_city") or "").strip()
        destination_city = (request.data.get("destination_city") or "").strip()
        if not departure_city or not destination_city:
            return Response(
                {"detail": "请输入出发地和目的地。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        days = int(request.data.get("days", 3))
        budget = int(request.data.get("budget", 3000))
        preferences = request.data.get("preferences", "")

        queryset = Destination.objects.all()
        destination_query = Q(name__icontains=destination_city) | Q(city__icontains=destination_city)
        destination_query |= Q(province__icontains=destination_city) | Q(summary__icontains=destination_city)
        destination_query |= Q(tags__icontains=destination_city)
        queryset = queryset.filter(destination_query).distinct()

        words = [item.strip() for item in preferences.split(",") if item.strip()]
        if words:
            preference_query = Q()
            for word in words:
                preference_query |= Q(tags__icontains=word) | Q(city__icontains=word) | Q(name__icontains=word)
            preferred_queryset = queryset.filter(preference_query).distinct()
            if preferred_queryset.exists():
                queryset = preferred_queryset

        selected = list(queryset.order_by("-is_hidden_gem", "-score")[: max(days, 3)])
        if not selected:
            return Response(
                {"detail": f"暂未找到和“{destination_city}”相关的景点，请换个目的地试试。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        trip = TripPlan.objects.create(
            user=request.user,
            title=f"{departure_city} - {destination_city}{days}日智能行程",
            departure_city=departure_city,
            destination_city=destination_city,
            days=days,
            budget=budget,
            preferences=preferences,
        )

        itinerary = defaultdict(list)
        for index, destination in enumerate(selected[:days], start=1):
            TripStop.objects.create(
                trip=trip,
                destination=destination,
                day_number=index,
                sequence=1,
                note=f"建议预留 {destination.suggested_days} 天深度体验。",
            )
            UserAction.objects.create(user=request.user, destination=destination, action_type="plan")
            itinerary[index].append(
                {
                    "destination_id": destination.id,
                    "destination_name": destination.name,
                    "city": destination.city,
                    "cover": destination.cover,
                    "note": f"预算友好度：{destination.budget_level}，最佳季节：{destination.best_season or '四季皆宜'}",
                }
            )

        return Response({"trip": TripPlanSerializer(trip).data, "itinerary": itinerary})
