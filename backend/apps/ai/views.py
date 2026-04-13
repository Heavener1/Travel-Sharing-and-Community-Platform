import json

from django.db.models import Q
from django.http import StreamingHttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import AIServiceError, chat_completion, chat_completion_stream, list_providers
from apps.travel.models import Destination


def sse_event(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_text_response(provider, model, prompt, temperature):
    def generate():
        content = ""
        chunk_count = 0
        yield sse_event("progress", {"progress": 10, "message": "已连接模型，开始生成"})
        try:
            for chunk in chat_completion_stream(provider=provider, model=model, prompt=prompt, temperature=temperature):
                chunk_count += 1
                content += chunk
                yield sse_event("content", {"chunk": chunk, "content": content})
                yield sse_event(
                    "progress",
                    {
                        "progress": min(15 + chunk_count * 4, 95),
                        "message": "AI 正在生成内容",
                    },
                )
            yield sse_event("progress", {"progress": 100, "message": "生成完成"})
            yield sse_event("done", {"content": content})
        except AIServiceError as exc:
            yield sse_event("error", {"detail": str(exc)})

    response = StreamingHttpResponse(generate(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


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
    for review in destination.reviews.all():
        rating_counts[review.rating] += 1
    review_lines = [
        f"{(getattr(getattr(review.user, 'profile', None), 'nickname', '') or review.user.username)}：{review.rating}星，评价：{review.content or '仅评分'}"
        for review in reviews
    ]
    return (
        f"{build_destination_context(destination)}"
        f"评分分布：5星{rating_counts[5]}条，4星{rating_counts[4]}条，3星{rating_counts[3]}条，2星{rating_counts[2]}条，1星{rating_counts[1]}条\n"
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


class ProviderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, _request):
        return Response(list_providers())


class TravelAssistantView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def build_prompt(request):
        return (
            "请基于以下旅行需求，生成一份适合旅游分享平台展示的智能旅行建议。"
            "请输出 3 个部分：1. 总体路线建议 2. 每日重点安排 3. 预算与避坑提醒。\n"
            f"出发地：{request.data.get('departure_city', '')}\n"
            f"目的地：{request.data.get('destination_city', '')}\n"
            f"天数：{request.data.get('days', '')}\n"
            f"预算：{request.data.get('budget', '')}\n"
            f"偏好：{request.data.get('preferences', '')}\n"
            f"当前系统行程草案：{request.data.get('draft_itinerary', '')}\n"
        )

    def post(self, request):
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        try:
            content = chat_completion(provider=provider, model=model, prompt=self.build_prompt(request), temperature=0.6)
            return Response({"content": content})
        except AIServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class TravelAssistantStreamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        prompt = TravelAssistantView.build_prompt(request)
        return stream_text_response(provider=provider, model=model, prompt=prompt, temperature=0.6)


class PostPolishView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def build_prompt(request):
        return (
            "请将以下旅游社区帖子润色为更适合发布的版本。"
            "要求：保留真实感，不夸张，不编造没有提供的信息。"
            "请按如下格式输出：\n"
            "标题：...\n"
            "正文：...\n"
            "标签建议：...\n"
            f"原标题：{request.data.get('title', '')}\n"
            f"原正文：{request.data.get('content', '')}\n"
            f"原标签：{request.data.get('tags', '')}\n"
        )

    def post(self, request):
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        try:
            content = chat_completion(provider=provider, model=model, prompt=self.build_prompt(request), temperature=0.8)
            return Response({"content": content})
        except AIServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PostPolishStreamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        prompt = PostPolishView.build_prompt(request)
        return stream_text_response(provider=provider, model=model, prompt=prompt, temperature=0.8)


class ScenicQAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def build_prompt(request, destination):
        return (
            "你是旅游平台的景点问答助手。"
            "请严格基于给定景点资料回答用户问题。"
            "如果资料里没有明确写到，就明确说明“根据当前系统资料暂时无法确认”，再给出保守建议。"
            "回答请使用中文，内容清晰、实用，适合旅游场景。\n"
            f"{build_destination_context(destination)}\n"
            f"用户问题：{request.data.get('question', '')}\n"
        )

    def post(self, request):
        destination_name = request.data.get("destination_name", "")
        destination = find_destination(destination_name)
        if not destination:
            return Response({"detail": "没有找到对应景点，请换个景点名称试试。"}, status=status.HTTP_404_NOT_FOUND)

        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        try:
            content = chat_completion(
                provider=provider,
                model=model,
                prompt=self.build_prompt(request, destination),
                temperature=0.5,
            )
            return Response(
                {
                    "destination_name": destination.name,
                    "destination_city": destination.city,
                    "content": content,
                }
            )
        except AIServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ScenicQAStreamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        destination_name = request.data.get("destination_name", "")
        destination = find_destination(destination_name)
        if not destination:
            return Response({"detail": "没有找到对应景点，请换个景点名称试试。"}, status=status.HTTP_404_NOT_FOUND)

        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")

        def generate():
            yield sse_event(
                "destination",
                {
                    "destination_name": destination.name,
                    "destination_city": destination.city,
                },
            )
            prompt = ScenicQAView.build_prompt(request, destination)
            content = ""
            chunk_count = 0
            yield sse_event("progress", {"progress": 10, "message": f"已锁定景点：{destination.name}"})
            try:
                for chunk in chat_completion_stream(provider=provider, model=model, prompt=prompt, temperature=0.5):
                    chunk_count += 1
                    content += chunk
                    yield sse_event("content", {"chunk": chunk, "content": content})
                    yield sse_event(
                        "progress",
                        {
                            "progress": min(15 + chunk_count * 4, 95),
                            "message": "AI 正在回答景点问题",
                        },
                    )
                yield sse_event("progress", {"progress": 100, "message": "问答完成"})
                yield sse_event("done", {"content": content})
            except AIServiceError as exc:
                yield sse_event("error", {"detail": str(exc)})

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class DestinationAnalysisStreamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        destination_id = request.data.get("destination_id")
        destination = Destination.objects.prefetch_related("hotels", "reviews", "reviews__user__profile").filter(pk=destination_id).first()
        if not destination:
            return Response({"detail": "没有找到对应景点。"}, status=status.HTTP_404_NOT_FOUND)

        provider = request.data.get("provider", "qwen")
        model = request.data.get("model")
        prompt = (
            "你是旅游平台的数据分析助手。"
            "请基于景点资料、评分统计和用户评价，对当前景点做一份适合前端展示的分析。"
            "请输出 4 个部分：1. 景点整体印象 2. 用户评分解读 3. 优势与短板 4. 适合人群与建议。"
            "请用中文回答，避免编造资料中没有的信息。\n"
            f"{build_destination_analysis_context(destination)}"
        )

        def generate():
            yield sse_event(
                "destination",
                {"destination_name": destination.name, "destination_city": destination.city},
            )
            content = ""
            chunk_count = 0
            yield sse_event("progress", {"progress": 10, "message": "已整理景点评分与评价数据"})
            try:
                for chunk in chat_completion_stream(provider=provider, model=model, prompt=prompt, temperature=0.4):
                    chunk_count += 1
                    content += chunk
                    yield sse_event("content", {"chunk": chunk, "content": content})
                    yield sse_event(
                        "progress",
                        {"progress": min(15 + chunk_count * 4, 95), "message": "AI 正在分析景点数据"},
                    )
                yield sse_event("progress", {"progress": 100, "message": "分析完成"})
                yield sse_event("done", {"content": content})
            except AIServiceError as exc:
                yield sse_event("error", {"detail": str(exc)})

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
