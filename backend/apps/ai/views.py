from django.db.models import Q
from django.http import StreamingHttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.chains import build_destination_analysis_chain, build_travel_assistant_chain
from apps.ai.langchain_service import (
    LangChainServiceError,
    destination_analysis_stream,
    post_polish,
    post_polish_stream,
    post_summary_stream,
    scenic_qa,
    scenic_qa_stream,
    travel_assistant,
    travel_assistant_stream,
)
from apps.ai.services import list_providers
from apps.common.utils import sse_event
from apps.social.models import Post
from apps.travel.models import Destination
from apps.users.utils import get_user_display_name


# ──────────────────────────────────────────────
# 通用流式输出辅助
# ──────────────────────────────────────────────

def _stream_langchain_response(stream_iterator, progress_message: str = "AI 正在生成内容"):
    """将 LangChain 流式输出包装为 SSE 事件流。"""

    def generate():
        content = ""
        chunk_count = 0
        yield sse_event("progress", {"progress": 10, "message": "已连接模型，开始生成"})
        try:
            for chunk in stream_iterator:
                chunk_count += 1
                content += chunk
                yield sse_event("content", {"chunk": chunk, "content": content})
                yield sse_event(
                    "progress",
                    {"progress": min(15 + chunk_count * 4, 95), "message": progress_message},
                )
            yield sse_event("progress", {"progress": 100, "message": "生成完成"})
            yield sse_event("done", {"content": content})
        except LangChainServiceError as exc:
            yield sse_event("error", {"detail": str(exc)})

    response = StreamingHttpResponse(generate(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


# ──────────────────────────────────────────────
# 景点上下文构建
# ──────────────────────────────────────────────

def build_destination_context(destination):
    hotels = list(destination.hotels.all()[:3])
    hotel_lines = [
        f"{hotel.name}，每晚约 {hotel.price_per_night} 元，亮点：{hotel.highlights or '交通方便'}"
        for hotel in hotels
    ]
    return (
        f"景点名称：{destination.name}\n"
        f"所在城市：{destination.city}\n"
        f"所在省份：{destination.province}\n"
        f"景点简介：{destination.summary}\n"
        f"标签：{destination.tags or '暂无'}\n"
        f"预算等级：{destination.budget_level}\n"
        f"最佳季节：{destination.best_season or '四季皆宜'}\n"
        f"参考评分：{destination.score}\n"
        f"门票价格：{destination.ticket_price}\n"
        f"建议游玩天数：{destination.suggested_days}\n"
        f"住宿推荐：{'；'.join(hotel_lines) if hotel_lines else '暂无酒店信息'}\n"
    )


def build_destination_analysis_context(destination):
    reviews = list(destination.reviews.select_related("user__profile").all()[:10])
    rating_counts = {star: 0 for star in range(1, 6)}
    if hasattr(destination, "_prefetched_objects_cache") and "reviews" in destination._prefetched_objects_cache:
        all_reviews = destination._prefetched_objects_cache["reviews"]
    else:
        all_reviews = list(destination.reviews.all())
    for review in all_reviews:
        rating_counts[review.rating] += 1
    review_lines = [
        f"{get_user_display_name(review.user)}：{review.rating}星，评价：{review.content or '仅评分'}"
        for review in reviews
    ]
    return (
        f"{build_destination_context(destination)}"
        f"评分分布：5星{rating_counts[5]}条，4星{rating_counts[4]}条，3星{rating_counts[3]}条，"
        f"2星{rating_counts[2]}条，1星{rating_counts[1]}条\n"
        f"用户评价样本：{'；'.join(review_lines) if review_lines else '暂无用户评价'}\n"
    )


def find_destination(destination_name):
    destination_name = (destination_name or "").strip()
    if not destination_name:
        return None
    queryset = Destination.objects.prefetch_related("hotels")
    exact_match = queryset.filter(name__iexact=destination_name).first()
    if exact_match:
        return exact_match
    fuzzy_query = (
        Q(name__icontains=destination_name)
        | Q(city__icontains=destination_name)
        | Q(province__icontains=destination_name)
        | Q(tags__icontains=destination_name)
        | Q(summary__icontains=destination_name)
    )
    return queryset.filter(fuzzy_query).order_by("-score").first()


# ──────────────────────────────────────────────
# 视图
# ──────────────────────────────────────────────

class ProviderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, _request):
        return Response(list_providers())


# ═══════════════════════════════════════════════
# 工作流 1：旅行助手
# ═══════════════════════════════════════════════

class TravelAssistantView(APIView):
    """LangChain 工作流：旅行助手"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        try:
            content = travel_assistant(
                provider=provider,
                departure_city=request.data.get("departure_city", ""),
                destination_city=request.data.get("destination_city", ""),
                days=request.data.get("days", ""),
                budget=request.data.get("budget", ""),
                preferences=request.data.get("preferences", ""),
                draft_itinerary=request.data.get("draft_itinerary", ""),
                model=model,
            )
            return Response({"content": content})
        except LangChainServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class TravelAssistantStreamView(APIView):
    """LangChain 工作流：旅行助手（流式）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        stream = travel_assistant_stream(
            provider=provider,
            departure_city=request.data.get("departure_city", ""),
            destination_city=request.data.get("destination_city", ""),
            days=request.data.get("days", ""),
            budget=request.data.get("budget", ""),
            preferences=request.data.get("preferences", ""),
            draft_itinerary=request.data.get("draft_itinerary", ""),
            model=model,
        )
        return _stream_langchain_response(stream, "AI 正在生成旅行建议")


# ═══════════════════════════════════════════════
# 工作流 2：景点智能问答
# ═══════════════════════════════════════════════

class ScenicQAView(APIView):
    """LangChain 工作流：景点智能问答"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        destination_name = request.data.get("destination_name", "")
        destination = find_destination(destination_name)
        if not destination:
            return Response(
                {"detail": "没有找到对应景点，请换个景点名称试试。"},
                status=status.HTTP_404_NOT_FOUND,
            )

        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        context = build_destination_context(destination)
        question = request.data.get("question", "")

        try:
            content = scenic_qa(provider=provider, context=context, question=question, model=model)
            return Response({
                "destination_name": destination.name,
                "destination_city": destination.city,
                "content": content,
            })
        except LangChainServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ScenicQAStreamView(APIView):
    """LangChain 工作流：景点智能问答（流式）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        destination_name = request.data.get("destination_name", "")
        destination = find_destination(destination_name)
        if not destination:
            return Response(
                {"detail": "没有找到对应景点，请换个景点名称试试。"},
                status=status.HTTP_404_NOT_FOUND,
            )

        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        context = build_destination_context(destination)
        question = request.data.get("question", "")

        def generate():
            yield sse_event("destination", {
                "destination_name": destination.name,
                "destination_city": destination.city,
            })
            yield sse_event("progress", {"progress": 5, "message": f"已锁定景点：{destination.name}"})

            content = ""
            chunk_count = 0
            try:
                for chunk in scenic_qa_stream(provider=provider, context=context, question=question, model=model):
                    chunk_count += 1
                    content += chunk
                    yield sse_event("content", {"chunk": chunk, "content": content})
                    yield sse_event(
                        "progress",
                        {"progress": min(10 + chunk_count * 4, 95), "message": "AI 正在回答景点问题"},
                    )
                yield sse_event("progress", {"progress": 100, "message": "问答完成"})
                yield sse_event("done", {"content": content})
            except LangChainServiceError as exc:
                yield sse_event("error", {"detail": str(exc)})

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


# ═══════════════════════════════════════════════
# 工作流 3：景点数据分析
# ═══════════════════════════════════════════════

class DestinationAnalysisStreamView(APIView):
    """LangChain 工作流：景点数据分析（流式）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        destination_id = request.data.get("destination_id")
        destination = (
            Destination.objects.prefetch_related("hotels", "reviews", "reviews__user__profile")
            .filter(pk=destination_id)
            .first()
        )
        if not destination:
            return Response({"detail": "没有找到对应景点。"}, status=status.HTTP_404_NOT_FOUND)

        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        context = build_destination_analysis_context(destination)

        def generate():
            yield sse_event("destination", {
                "destination_name": destination.name,
                "destination_city": destination.city,
            })
            yield sse_event("progress", {"progress": 10, "message": "已整理景点评分与评价数据"})

            content = ""
            chunk_count = 0
            try:
                for chunk in destination_analysis_stream(provider=provider, context=context, model=model):
                    chunk_count += 1
                    content += chunk
                    yield sse_event("content", {"chunk": chunk, "content": content})
                    yield sse_event(
                        "progress",
                        {"progress": min(15 + chunk_count * 4, 95), "message": "AI 正在分析景点数据"},
                    )
                yield sse_event("progress", {"progress": 100, "message": "分析完成"})
                yield sse_event("done", {"content": content})
            except LangChainServiceError as exc:
                yield sse_event("error", {"detail": str(exc)})

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


# ═══════════════════════════════════════════════
# 工作流 4：内容润色
# ═══════════════════════════════════════════════

class PostPolishView(APIView):
    """LangChain 工作流：内容润色"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        try:
            content = post_polish(
                provider=provider,
                title=request.data.get("title", ""),
                content=request.data.get("content", ""),
                tags=request.data.get("tags", ""),
                model=model,
            )
            return Response({"content": content})
        except LangChainServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PostPolishStreamView(APIView):
    """LangChain 工作流：内容润色（流式）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        stream = post_polish_stream(
            provider=provider,
            title=request.data.get("title", ""),
            content=request.data.get("content", ""),
            tags=request.data.get("tags", ""),
            model=model,
        )
        return _stream_langchain_response(stream, "AI 正在润色内容")


# ═══════════════════════════════════════════════
# 工作流 5：帖子总结
# ═══════════════════════════════════════════════

class PostSummaryStreamView(APIView):
    """LangChain 工作流：帖子总结（流式）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        post_id = request.data.get("post_id")
        post = (
            Post.objects.select_related("destination", "author", "author__profile")
            .prefetch_related("comments__author__profile", "comments__replies")
            .filter(pk=post_id)
            .first()
        )
        if not post:
            return Response({"detail": "没有找到对应帖子。"}, status=status.HTTP_404_NOT_FOUND)

        # 构建评论摘要
        comments = list(post.comments.filter(parent__isnull=True)[:8])
        comment_lines = []
        for comment in comments:
            author_name = get_user_display_name(comment.author)
            reply_count = comment.replies.count()
            comment_lines.append(f"{author_name}：{comment.content}（回复 {reply_count} 条）")

        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        destination_name = post.destination.name if post.destination else "未关联景点"

        stream = post_summary_stream(
            provider=provider,
            title=post.title,
            destination_name=destination_name,
            content=post.content,
            tags=post.tags or "无",
            comments_summary="；".join(comment_lines) if comment_lines else "当前暂无评论",
            model=model,
        )
        return _stream_langchain_response(stream, "AI 正在生成总结")
