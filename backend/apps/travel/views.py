import json

from django.db.models import Avg, Q
from django.http import StreamingHttpResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import AIServiceError, chat_completion_stream, list_providers
from apps.social.models import UserAction
from apps.travel.models import Destination, DestinationReview, Hotel
from apps.travel.serializers import (
    DestinationCreateSerializer,
    DestinationDetailSerializer,
    DestinationReviewCreateSerializer,
    DestinationSerializer,
    HotelSerializer,
)
from apps.travel.services import search_destination_ids, upload_fileobj


def sse_event(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def get_destination_queryset():
    return Destination.objects.prefetch_related("hotels", "reviews", "reviews__user__profile").all()


def update_destination_score(destination):
    average = destination.reviews.aggregate(avg=Avg("rating")).get("avg")
    if average is not None:
        destination.score = round(float(average), 1)
        destination.save(update_fields=["score"])


def filter_destinations_by_keyword(queryset, keyword):
    keyword_lower = keyword.lower()
    items = list(queryset)
    return [
        item
        for item in items
        if keyword_lower in item.name.lower()
        or keyword_lower in item.city.lower()
        or keyword_lower in item.province.lower()
        or keyword_lower in item.tags.lower()
        or keyword_lower in item.summary.lower()
    ]


def get_es_results(keyword, hidden_gem=False, limit=6):
    queryset = get_destination_queryset()
    try:
        ids = search_destination_ids(keyword)
        if not ids:
            return []
        preserved = {pk: index for index, pk in enumerate(ids)}
        items = sorted(
            queryset.filter(id__in=ids),
            key=lambda item: preserved.get(item.id, 9999),
        )
        if hidden_gem:
            items = [item for item in items if item.is_hidden_gem]
        return items[:limit]
    except Exception:
        return []


def get_db_results(keyword, hidden_gem=False, limit=6):
    queryset = get_destination_queryset()
    items = filter_destinations_by_keyword(queryset, keyword)
    if hidden_gem:
        items = [item for item in items if item.is_hidden_gem]
    return items[:limit]


def pick_ai_provider():
    provider_info = list_providers()
    for provider in ("qwen", "kimi"):
        if provider_info.get(provider, {}).get("configured"):
            return provider
    return None


def build_ai_search_prompt(keyword, source_items):
    context = [
        {
            "name": item.name,
            "city": item.city,
            "province": item.province,
            "summary": item.summary,
            "tags": item.tags,
            "best_season": item.best_season,
            "budget_level": item.budget_level,
            "score": float(item.score),
        }
        for item in source_items[:6]
    ]
    return (
        "你是旅游平台的智能搜索助手。"
        "请根据用户搜索词和候选景点，生成一段适合前端实时展示的中文搜索建议。"
        "输出结构请按以下顺序自然组织：1. 一句话总结 2. 推荐优先看的景点 3. 玩法建议 4. 适合人群。"
        "不要编造过于具体的票价、地址或营业时间。\n"
        f"用户搜索词：{keyword}\n"
        f"候选景点：{json.dumps(context, ensure_ascii=False)}\n"
    )


class DestinationListView(generics.ListCreateAPIView):
    serializer_class = DestinationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = get_destination_queryset()
        keyword = self.request.query_params.get("q")
        search_mode = self.request.query_params.get("search_mode")
        hidden_gem = self.request.query_params.get("hidden_gem")
        if keyword:
            if search_mode == "es":
                items = get_es_results(keyword, hidden_gem == "true", limit=20)
                if items:
                    return items
            queryset = filter_destinations_by_keyword(queryset, keyword)
        if hidden_gem == "true":
            if isinstance(queryset, list):
                queryset = [item for item in queryset if item.is_hidden_gem]
            else:
                queryset = queryset.filter(is_hidden_gem=True)
        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DestinationCreateSerializer
        return DestinationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        destination = serializer.save()
        return Response(DestinationSerializer(destination, context={"request": request}).data, status=status.HTTP_201_CREATED)


class SmartSearchView(APIView):
    def get(self, request):
        keyword = (request.query_params.get("q") or "").strip()
        hidden_gem = request.query_params.get("hidden_gem") == "true"
        if not keyword:
            featured = get_destination_queryset().order_by("-is_hidden_gem", "-score")[:8]
            return Response(
                {
                    "keyword": "",
                    "es_results": [],
                    "db_results": [],
                    "ai_summary": "输入关键词后，可同时检索 ElasticSearch、MySQL 和 AI 智能推荐结果。",
                    "ai_provider": "",
                    "ai_error": "",
                    "featured_results": DestinationSerializer(featured, many=True, context={"request": request}).data,
                }
            )

        es_items = get_es_results(keyword, hidden_gem=hidden_gem, limit=6)
        db_items = get_db_results(keyword, hidden_gem=hidden_gem, limit=6)
        provider = pick_ai_provider()
        ai_summary = ""
        ai_error = ""
        if provider:
            try:
                ai_summary = "".join(
                    chat_completion_stream(
                        provider=provider,
                        prompt=build_ai_search_prompt(keyword, es_items + db_items),
                        temperature=0.4,
                    )
                )
            except AIServiceError as exc:
                ai_error = str(exc)
        else:
            ai_error = "AI 搜索暂未配置，当前仅展示 ES 与数据库结果。"

        return Response(
            {
                "keyword": keyword,
                "es_results": DestinationSerializer(es_items, many=True, context={"request": request}).data,
                "db_results": DestinationSerializer(db_items, many=True, context={"request": request}).data,
                "ai_summary": ai_summary,
                "ai_provider": provider or "",
                "ai_error": ai_error,
                "featured_results": [],
            }
        )


class SmartSearchStreamView(APIView):
    def get(self, request):
        keyword = (request.query_params.get("q") or "").strip()
        hidden_gem = request.query_params.get("hidden_gem") == "true"

        def generate():
            if not keyword:
                featured = get_destination_queryset().order_by("-is_hidden_gem", "-score")[:8]
                yield sse_event(
                    "featured_results",
                    {"items": DestinationSerializer(featured, many=True, context={"request": request}).data},
                )
                yield sse_event("progress", {"progress": 100, "message": "已加载热门景点"})
                yield sse_event("done", {"content": ""})
                return

            yield sse_event("progress", {"progress": 10, "message": "正在检索 ElasticSearch"})
            es_items = get_es_results(keyword, hidden_gem=hidden_gem, limit=6)
            yield sse_event(
                "es_results",
                {"items": DestinationSerializer(es_items, many=True, context={"request": request}).data},
            )

            yield sse_event("progress", {"progress": 35, "message": "正在检索数据库"})
            db_items = get_db_results(keyword, hidden_gem=hidden_gem, limit=6)
            yield sse_event(
                "db_results",
                {"items": DestinationSerializer(db_items, many=True, context={"request": request}).data},
            )

            provider = pick_ai_provider()
            if not provider:
                yield sse_event("error", {"detail": "AI 搜索暂未配置，当前仅展示 ES 与数据库结果。"})
                yield sse_event("progress", {"progress": 100, "message": "检索完成"})
                yield sse_event("done", {"content": ""})
                return

            combined = []
            seen_ids = set()
            for item in es_items + db_items:
                if item.id in seen_ids:
                    continue
                seen_ids.add(item.id)
                combined.append(item)

            yield sse_event("provider", {"provider": provider})
            yield sse_event("progress", {"progress": 55, "message": "AI 正在生成智能导览"})
            content = ""
            chunk_count = 0
            try:
                for chunk in chat_completion_stream(
                    provider=provider,
                    prompt=build_ai_search_prompt(keyword, combined),
                    temperature=0.4,
                ):
                    chunk_count += 1
                    content += chunk
                    yield sse_event("ai_content", {"chunk": chunk, "content": content})
                    yield sse_event(
                        "progress",
                        {"progress": min(60 + chunk_count * 3, 95), "message": "AI 正在完善搜索建议"},
                    )
                yield sse_event("progress", {"progress": 100, "message": "智能搜索完成"})
                yield sse_event("done", {"content": content})
            except AIServiceError as exc:
                yield sse_event("error", {"detail": str(exc)})
                yield sse_event("progress", {"progress": 100, "message": "已返回基础检索结果"})
                yield sse_event("done", {"content": content})

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class DestinationDetailView(generics.RetrieveAPIView):
    queryset = get_destination_queryset()
    serializer_class = DestinationDetailSerializer


class DestinationReviewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        destination = generics.get_object_or_404(Destination, pk=pk)
        if DestinationReview.objects.filter(destination=destination, user=request.user).exists():
            return Response({"detail": "你已经评价过这个景点了。"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DestinationReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DestinationReview.objects.create(destination=destination, user=request.user, **serializer.validated_data)
        update_destination_score(destination)
        destination.refresh_from_db()
        destination = get_destination_queryset().get(pk=destination.pk)
        return Response(DestinationDetailSerializer(destination, context={"request": request}).data, status=status.HTTP_201_CREATED)


class HotelListView(generics.ListAPIView):
    serializer_class = HotelSerializer

    def get_queryset(self):
        queryset = Hotel.objects.select_related("destination")
        destination_id = self.request.query_params.get("destination")
        if destination_id:
            queryset = queryset.filter(destination_id=destination_id)
        return queryset


class RecommendationView(APIView):
    def get(self, request):
        base_qs = Destination.objects.all()
        if not request.user.is_authenticated:
            items = base_qs.order_by("-is_hidden_gem", "-score")[:6]
            return Response(DestinationSerializer(items, many=True, context={"request": request}).data)

        actions = UserAction.objects.filter(user=request.user).select_related("destination")
        keywords = []
        for action in actions:
            if action.destination and action.destination.tags:
                keywords.extend([tag.strip() for tag in action.destination.tags.split(",") if tag.strip()])

        queryset = base_qs
        if keywords:
            query = Q()
            for word in keywords[:5]:
                query |= Q(tags__icontains=word) | Q(city__icontains=word)
            queryset = queryset.filter(query).distinct()

        items = list(queryset.order_by("-score")[:6])
        if len(items) < 6:
            fallback_ids = {item.id for item in items}
            fallback = base_qs.exclude(id__in=fallback_ids).order_by("-is_hidden_gem", "-score")[: 6 - len(items)]
            items.extend(list(fallback))
        return Response(DestinationSerializer(items, many=True, context={"request": request}).data)


class TravelDashboardView(APIView):
    def get(self, request):
        return Response(
            {
                "destination_count": Destination.objects.count(),
                "hidden_gem_count": Destination.objects.filter(is_hidden_gem=True).count(),
                "hotel_count": Hotel.objects.count(),
                "featured_destinations": DestinationSerializer(
                    Destination.objects.prefetch_related("hotels", "reviews").order_by("-score")[:3],
                    many=True,
                    context={"request": request},
                ).data,
            }
        )


class UploadImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "缺少文件"}, status=status.HTTP_400_BAD_REQUEST)
        upload_info = upload_fileobj(file_obj, folder="covers")
        return Response(upload_info)
