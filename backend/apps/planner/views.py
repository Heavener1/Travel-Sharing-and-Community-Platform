from collections import defaultdict
import logging

from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.langchain_service import LangChainServiceError, trip_planner
from apps.common.utils import track_destination_action
from apps.planner.models import TripPlan, TripStop
from apps.planner.serializers import TripPlanSerializer
from apps.travel.models import Destination

logger = logging.getLogger("apps.planner")


class TripPlanListCreateView(generics.ListCreateAPIView):
    serializer_class = TripPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TripPlan.objects.filter(user=self.request.user).prefetch_related("stops__destination")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TripGeneratorView(APIView):
    """LangChain 工作流：景点规划 — DB 搜索 + AI 生成行程方案"""

    permission_classes = [permissions.IsAuthenticated]
    MAX_CANDIDATES = 100

    @staticmethod
    def _build_candidates_text(destinations):
        """将候选景点列表格式化为 LLM 输入文本。"""
        lines = []
        for i, d in enumerate(destinations, 1):
            lines.append(
                f"{i}. {d.name}（{d.city}）\n"
                f"   简介：{d.summary[:80]}\n"
                f"   标签：{d.tags or '无'} | 预算：{d.budget_level} | "
                f"最佳季节：{d.best_season or '四季皆宜'} | 评分：{d.score}"
            )
        return "\n".join(lines)

    @staticmethod
    def _parse_ai_notes(ai_plan_text: str, days: int) -> dict[int, str]:
        """将 AI 生成的行程文本按天解析为 {day_number: note} 映射。"""
        day_notes: dict[int, str] = {}
        for line in ai_plan_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            for day_num in range(1, days + 1):
                if line.startswith(f"第{day_num}天") or line.startswith(f"Day {day_num}"):
                    note = line.split("—", 1)[-1].split("：", 1)[-1].strip()
                    if note:
                        day_notes[day_num] = note[:200]
                    break
        return day_notes

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

        # ── DB 搜索 ──
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

        queryset = queryset.order_by("-is_hidden_gem", "-score")[: self.MAX_CANDIDATES]
        selected = list(queryset[: max(days, 3)])
        if not selected:
            return Response(
                {"detail": f"暂未找到和'{destination_city}'相关的景点，请换个目的地试试。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── LangChain 景点规划 ──
        candidates_text = self._build_candidates_text(selected)
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        ai_plan = ""
        ai_error = ""
        try:
            ai_plan = trip_planner(
                provider=provider,
                destination_city=destination_city,
                days=days,
                budget=budget,
                preferences=preferences,
                candidates=candidates_text,
                model=model,
            )
        except LangChainServiceError as exc:
            logger.warning("Trip planner AI call failed: %s", exc)
            ai_error = str(exc)

        day_notes = self._parse_ai_notes(ai_plan, days)

        # ── 创建行程 ──
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
            note = day_notes.get(index) or f"建议预留 {destination.suggested_days} 天深度体验。"
            TripStop.objects.create(
                trip=trip,
                destination=destination,
                day_number=index,
                sequence=1,
                note=note,
            )
            track_destination_action(request.user, destination, "plan")
            itinerary[index].append({
                "destination_id": destination.id,
                "destination_name": destination.name,
                "city": destination.city,
                "cover": destination.cover,
                "note": note,
            })

        return Response({
            "trip": TripPlanSerializer(trip).data,
            "itinerary": itinerary,
            "ai_plan": ai_plan,
            "ai_error": ai_error,
        })
