"""
旅行模块视图 — 景点 CRUD、智能搜索（ES + AI 流式）、评价、收藏、个性化推荐、相关推荐、图片上传。
"""

import json
import logging
from collections import Counter, defaultdict

from django.db.models import Avg
from django.http import StreamingHttpResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import AIServiceError, chat_completion_stream, list_providers
from apps.common.utils import build_user_preference_profile, extract_tags, sse_event, track_destination_action
from apps.social.models import UserAction
from apps.travel.models import Destination, DestinationReview, FavoriteDestination, Hotel
from apps.travel.serializers import (
    DestinationCreateSerializer,
    DestinationDetailSerializer,
    DestinationReviewCreateSerializer,
    DestinationSerializer,
    FavoriteDestinationSerializer,
    HotelSerializer,
)
from apps.travel.services import search_destination_ids, upload_fileobj

logger = logging.getLogger("apps.travel")


def get_destination_queryset():
    return Destination.objects.prefetch_related("hotels", "reviews", "reviews__user__profile", "favorites").all()


def update_destination_score(destination):
    """根据景点所有评价的均分更新 score 字段。"""
    average = destination.reviews.aggregate(avg=Avg("rating")).get("avg")
    if average is not None:
        destination.score = round(float(average), 1)
        destination.save(update_fields=["score"])


def search_es(keyword, hidden_gem=False, limit=20):
    """ES 全文检索：返回按 ES 评分排序的 Destination 对象列表。ES 暂不可用时返回空列表。"""
    try:
        ids = search_destination_ids(keyword)
        if not ids:
            return []
        preserved = {pk: index for index, pk in enumerate(ids)}
        queryset = get_destination_queryset().filter(id__in=ids)
        items = sorted(queryset, key=lambda item: preserved.get(item.id, 9999))
        if hidden_gem:
            items = [item for item in items if item.is_hidden_gem]
        return items[:limit]
    except Exception:
        logger.warning("ES search failed for keyword=%s", keyword, exc_info=True)
        return []


def pick_ai_provider():
    """从已配置的 AI 提供方中选择一个可用实例（优先千问，其次 Kimi）。"""
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
        "输出结构按以下顺序自然组织：1. 一句话总结 2. 推荐优先看的景点 3. 玩法建议 4. 适合人群。"
        "不要编造过于具体的票价、地址或营业时间。\n"
        f"用户搜索词：{keyword}\n"
        f"候选景点：{json.dumps(context, ensure_ascii=False)}\n"
    )


def personalized_destination_queryset(user):
    """根据用户行为（浏览/点赞/评价/收藏/行程）对景点加权排序，生成个性化推荐列表。"""
    base_qs = Destination.objects.all()
    if not user.is_authenticated:
        return base_qs.order_by("-is_hidden_gem", "-score")

    actions = UserAction.objects.filter(user=user).select_related("destination")
    favorites = FavoriteDestination.objects.filter(user=user).select_related("destination")
    reviews = DestinationReview.objects.filter(user=user).select_related("destination")

    weight_map = defaultdict(float)
    tag_counter = Counter()
    city_counter = Counter()
    province_counter = Counter()

    for action in actions:
        if not action.destination:
            continue
        if action.action_type == "view":
            weight_map[action.destination_id] += 1
        elif action.action_type == "like":
            weight_map[action.destination_id] += 3
        elif action.action_type == "plan":
            weight_map[action.destination_id] += 4
        elif action.action_type == "review":
            weight_map[action.destination_id] += 5
        elif action.action_type == "favorite":
            weight_map[action.destination_id] += 6
        elif action.action_type == "post":
            weight_map[action.destination_id] += 4
        for tag in (action.destination.tags or "").split(","):
            tag = tag.strip()
            if tag:
                tag_counter[tag] += 1
        if action.destination.city:
            city_counter[action.destination.city] += 1
        if action.destination.province:
            province_counter[action.destination.province] += 1

    for favorite in favorites:
        weight_map[favorite.destination_id] += 8

    for review in reviews:
        weight_map[review.destination_id] += 6 + float(review.rating)

    items = list(base_qs[:500])
    scored = []
    for item in items:
        score = weight_map.get(item.id, 0) + float(item.score)
        for tag in [tag.strip() for tag in (item.tags or "").split(",") if tag.strip()]:
            score += tag_counter.get(tag, 0) * 0.8
        score += city_counter.get(item.city, 0) * 0.8
        score += province_counter.get(item.province, 0) * 0.5
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


class DestinationListView(generics.ListCreateAPIView):
    serializer_class = DestinationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        keyword = (self.request.query_params.get("q") or "").strip()
        hidden_gem = self.request.query_params.get("hidden_gem") == "true"

        if keyword:
            items = search_es(keyword, hidden_gem=hidden_gem, limit=20)
            if items:
                return items
            return Destination.objects.none()

        queryset = get_destination_queryset()
        if hidden_gem:
            queryset = queryset.filter(is_hidden_gem=True)
        if self.request.query_params.get("ordering"):
            return queryset
        return queryset.order_by("-is_hidden_gem", "-score")

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
    """智能搜索 — 无关键词时展示个性化推荐，有关键词时 ES 检索 + AI 摘要。"""

    def get(self, request):
        keyword = (request.query_params.get("q") or "").strip()
        hidden_gem = request.query_params.get("hidden_gem") == "true"

        if not keyword:
            featured = (
                personalized_destination_queryset(request.user)[:8]
                if request.user.is_authenticated
                else get_destination_queryset().order_by("-is_hidden_gem", "-score")[:8]
            )
            return Response(
                {
                    "keyword": "",
                    "results": [],
                    "ai_summary": "",
                    "ai_provider": "",
                    "ai_error": "",
                    "featured_results": DestinationSerializer(featured, many=True, context={"request": request}).data,
                }
            )

        items = search_es(keyword, hidden_gem=hidden_gem, limit=10)
        provider = pick_ai_provider()
        ai_summary = ""
        ai_error = ""
        if provider and items:
            try:
                ai_summary = "".join(
                    chat_completion_stream(
                        provider=provider,
                        prompt=build_ai_search_prompt(keyword, items),
                        temperature=0.4,
                    )
                )
            except AIServiceError as exc:
                ai_error = str(exc)
        elif not provider:
            ai_error = "AI 服务暂未配置。"

        return Response(
            {
                "keyword": keyword,
                "results": DestinationSerializer(items, many=True, context={"request": request}).data,
                "ai_summary": ai_summary,
                "ai_provider": provider or "",
                "ai_error": ai_error,
                "featured_results": [],
            }
        )


class SmartSearchStreamView(APIView):
    """SSE 流式智能搜索 — 先返回 ES 结果，再流式输出 AI 导览摘要。"""

    def get(self, request):
        keyword = (request.query_params.get("q") or "").strip()
        hidden_gem = request.query_params.get("hidden_gem") == "true"

        def generate():
            if not keyword:
                featured = (
                    personalized_destination_queryset(request.user)[:8]
                    if request.user.is_authenticated
                    else get_destination_queryset().order_by("-is_hidden_gem", "-score")[:8]
                )
                yield sse_event(
                    "featured_results",
                    {"items": DestinationSerializer(featured, many=True, context={"request": request}).data},
                )
                yield sse_event("progress", {"progress": 100, "message": "已加载热门景点"})
                yield sse_event("done", {"content": ""})
                return

            yield sse_event("progress", {"progress": 10, "message": "正在检索 ElasticSearch"})
            items = search_es(keyword, hidden_gem=hidden_gem, limit=10)
            yield sse_event("es_results", {"items": DestinationSerializer(items, many=True, context={"request": request}).data})

            provider = pick_ai_provider()
            if not provider:
                yield sse_event("progress", {"progress": 100, "message": "搜索完成（AI 未配置）"})
                yield sse_event("done", {"content": ""})
                return

            if not items:
                yield sse_event("progress", {"progress": 100, "message": "未找到匹配的景点"})
                yield sse_event("done", {"content": ""})
                return

            yield sse_event("provider", {"provider": provider})
            yield sse_event("progress", {"progress": 55, "message": "AI 正在生成智能导览"})
            content = ""
            chunk_count = 0
            try:
                for chunk in chat_completion_stream(provider=provider, prompt=build_ai_search_prompt(keyword, items), temperature=0.4):
                    chunk_count += 1
                    content += chunk
                    yield sse_event("ai_content", {"chunk": chunk, "content": content})
                    yield sse_event("progress", {"progress": min(60 + chunk_count * 3, 95), "message": "AI 正在完善搜索建议"})
                yield sse_event("progress", {"progress": 100, "message": "智能搜索完成"})
                yield sse_event("done", {"content": content})
            except AIServiceError as exc:
                yield sse_event("error", {"detail": str(exc)})
                yield sse_event("progress", {"progress": 100, "message": "已返回检索结果"})
                yield sse_event("done", {"content": content})

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class DestinationDetailView(generics.RetrieveAPIView):
    queryset = get_destination_queryset()
    serializer_class = DestinationDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        track_destination_action(request.user, instance, "view")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class DestinationReviewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        destination = generics.get_object_or_404(Destination, pk=pk)
        if DestinationReview.objects.filter(destination=destination, user=request.user).exists():
            return Response({"detail": "你已经评价过这个景点了。"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DestinationReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = DestinationReview.objects.create(destination=destination, user=request.user, **serializer.validated_data)
        update_destination_score(destination)
        track_destination_action(request.user, destination, "review")
        destination.refresh_from_db()
        destination = get_destination_queryset().get(pk=destination.pk)
        return Response(DestinationDetailSerializer(destination, context={"request": request}).data, status=status.HTTP_201_CREATED)


class FavoriteDestinationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = FavoriteDestination.objects.filter(user=request.user).select_related("destination")
        serializer = FavoriteDestinationSerializer(queryset, many=True, context={"request": request})
        return Response({"results": serializer.data})


class FavoriteDestinationToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        destination = generics.get_object_or_404(Destination, pk=pk)
        favorite, created = FavoriteDestination.objects.get_or_create(destination=destination, user=request.user)
        if created:
            track_destination_action(request.user, destination, "favorite")
            return Response({"favorited": True}, status=status.HTTP_201_CREATED)
        favorite.delete()
        return Response({"favorited": False}, status=status.HTTP_200_OK)


class DestinationRelatedView(APIView):
    """景点相关推荐 — 基于标签重合度、地理位置和用户偏好计算相关景点和帖子的综合评分。"""
    permission_classes = [permissions.AllowAny]
    MAX_CANDIDATES = 200
    MAX_POSTS = 200

    def get(self, request, pk):
        current_destination = generics.get_object_or_404(get_destination_queryset(), pk=pk)
        current_tags = set(extract_tags(current_destination.tags))
        profile = build_user_preference_profile(request.user)

        candidate_destinations = get_destination_queryset().exclude(pk=current_destination.pk)[: self.MAX_CANDIDATES]
        scored_destinations = []
        for item in candidate_destinations:
            item_tags = set(extract_tags(item.tags))
            shared_tags = len(current_tags & item_tags)
            same_province = 2 if item.province == current_destination.province else 0
            same_city = 2 if item.city == current_destination.city else 0
            affinity = (
                profile["destination_counter"].get(item.id, 0) * 0.6
                + profile["city_counter"].get(item.city, 0) * 0.4
                + profile["province_counter"].get(item.province, 0) * 0.25
                + sum(profile["tag_counter"].get(tag, 0) for tag in item_tags) * 0.2
            )
            score = shared_tags * 1.8 + same_province + same_city + float(item.score) * 0.2 + affinity
            if score > 0:
                scored_destinations.append((score, item))
        scored_destinations.sort(key=lambda pair: pair[0], reverse=True)
        related_destinations = [item for _, item in scored_destinations[:12]]

        # Delayed import avoids cross-module import cycles during app loading.
        from apps.social.models import FavoritePost, Post, PostLike

        post_favorites = FavoritePost.objects.filter(user=request.user).select_related("post__destination") if request.user.is_authenticated else []
        liked_posts = PostLike.objects.filter(user=request.user).select_related("post__destination") if request.user.is_authenticated else []
        user_post_destination_boost = Counter()
        for favorite in post_favorites:
            if favorite.post.destination_id:
                user_post_destination_boost[favorite.post.destination_id] += 4
        for like in liked_posts:
            if like.post.destination_id:
                user_post_destination_boost[like.post.destination_id] += 2

        scored_posts = []
        for item in (
            Post.objects.filter(status="approved")
            .select_related("author", "destination")
            .prefetch_related("comments", "likes", "favorites")[: self.MAX_POSTS]
        ):
            item_tags = set(extract_tags(item.tags))
            shared_tags = len(current_tags & item_tags)
            same_destination = 4 if item.destination_id == current_destination.id or getattr(item.destination, "name", "") == current_destination.name else 0
            affinity = 0
            if item.destination:
                affinity += profile["destination_counter"].get(item.destination_id, 0) * 0.4
                affinity += user_post_destination_boost.get(item.destination_id, 0) * 0.5
                affinity += sum(profile["tag_counter"].get(tag, 0) for tag in item_tags) * 0.18
            score = shared_tags * 1.6 + same_destination + item.likes.count() * 0.08 + item.comments.filter(status="approved").count() * 0.1 + affinity
            if score > 0:
                scored_posts.append((score, item))
        scored_posts.sort(key=lambda pair: pair[0], reverse=True)
        related_posts = [item for _, item in scored_posts[:12]]

        from apps.social.serializers import PostListSerializer

        return Response(
            {
                "related_destinations": DestinationSerializer(related_destinations, many=True, context={"request": request}).data,
                "related_posts": PostListSerializer(related_posts, many=True, context={"request": request}).data,
            }
        )


class HotelListView(generics.ListAPIView):
    serializer_class = HotelSerializer

    def get_queryset(self):
        queryset = Hotel.objects.select_related("destination")
        destination_id = self.request.query_params.get("destination")
        if destination_id:
            queryset = queryset.filter(destination_id=destination_id)
        return queryset


class RecommendationView(APIView):
    """个性化推荐 — 认证用户基于行为画像推荐，匿名用户按评分排序。"""

    def get(self, request):
        if not request.user.is_authenticated:
            items = Destination.objects.all().order_by("-is_hidden_gem", "-score")[:6]
            return Response(DestinationSerializer(items, many=True, context={"request": request}).data)

        items = personalized_destination_queryset(request.user)[:6]
        return Response(DestinationSerializer(items, many=True, context={"request": request}).data)


class TravelDashboardView(APIView):
    def get(self, request):
        featured = personalized_destination_queryset(request.user)[:3] if request.user.is_authenticated else Destination.objects.prefetch_related("hotels", "reviews").order_by("-score")[:3]
        return Response(
            {
                "destination_count": Destination.objects.count(),
                "hidden_gem_count": Destination.objects.filter(is_hidden_gem=True).count(),
                "hotel_count": Hotel.objects.count(),
                "featured_destinations": DestinationSerializer(featured, many=True, context={"request": request}).data,
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
