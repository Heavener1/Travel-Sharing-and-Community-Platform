from collections import defaultdict
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from apps.social.models import Post, PostComment, PostLike, UserAction
from apps.social.serializers import PostCommentSerializer, PostCreateSerializer, PostSerializer, PostUpdateSerializer
from apps.travel.models import Destination, DestinationReview


TIME_SEGMENTS = [
    (0, 5, "00:00-05:59"),
    (6, 11, "06:00-11:59"),
    (12, 17, "12:00-17:59"),
    (18, 23, "18:00-23:59"),
]


class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        queryset = Post.objects.select_related("author", "destination").prefetch_related("comments", "likes")
        if self.request.user.is_staff:
            return queryset
        if self.request.user.is_authenticated:
            return queryset.filter(Q(status="approved") | Q(author=self.request.user)).distinct()
        return queryset.filter(status="approved")

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PostCreateSerializer
        return PostSerializer

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user, status="approved")
        if post.destination:
            UserAction.objects.create(user=self.request.user, destination=post.destination, action_type="view")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        post = Post.objects.select_related("author", "destination").prefetch_related("comments", "likes").get(pk=serializer.instance.pk)
        output = PostSerializer(post, context={"request": request}).data
        return Response(output, status=status.HTTP_201_CREATED)


class PostDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        queryset = Post.objects.select_related("author", "destination").prefetch_related("comments__author", "likes")
        if self.request.user.is_staff:
            return queryset
        if self.request.user.is_authenticated:
            return queryset.filter(Q(status="approved") | Q(author=self.request.user)).distinct()
        return queryset.filter(status="approved")

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return PostUpdateSerializer
        return PostSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff and instance.author_id != request.user.id:
            raise permissions.PermissionDenied("只有帖子作者可以编辑重新发布。")
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(status="approved", review_note="")
        output = PostSerializer(instance, context={"request": request}).data
        return Response(output)


class CommentCreateView(generics.CreateAPIView):
    serializer_class = PostCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post = Post.objects.get(pk=self.kwargs["post_id"])
        if post.status != "approved" and not self.request.user.is_staff and post.author != self.request.user:
            raise permissions.PermissionDenied("该帖子尚未通过审核")
        serializer.save(author=self.request.user, post=post, status="approved")


class LikeToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        post = Post.objects.get(pk=post_id)
        like, created = PostLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            return Response({"liked": False}, status=status.HTTP_200_OK)

        if post.destination:
            UserAction.objects.create(user=request.user, destination=post.destination, action_type="like")
        return Response({"liked": True}, status=status.HTTP_201_CREATED)


class ModerationSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, _request):
        return Response(
            {
                "pending_posts": Post.objects.filter(status="pending").count(),
                "pending_comments": PostComment.objects.filter(status="pending").count(),
            }
        )


class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, _request):
        posts = Post.objects.order_by("created_at")
        bucket_map = defaultdict(lambda: {label: 0 for _, _, label in TIME_SEGMENTS})

        for post in posts:
            local_dt = timezone.localtime(post.created_at)
            day_label = local_dt.strftime("%Y-%m-%d")
            for start, end, label in TIME_SEGMENTS:
                if start <= local_dt.hour <= end:
                    bucket_map[day_label][label] += 1
                    break

        timeline = []
        for date_label in sorted(bucket_map.keys()):
            segments = [
                {"label": label, "count": bucket_map[date_label][label]}
                for _, _, label in TIME_SEGMENTS
            ]
            timeline.append(
                {
                    "date": date_label,
                    "total": sum(item["count"] for item in segments),
                    "segments": segments,
                }
            )

        today = timezone.localdate()
        recent_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        user_trend_map = {
            item["date_joined__date"]: item["count"]
            for item in User.objects.filter(date_joined__date__gte=recent_days[0])
            .values("date_joined__date")
            .annotate(count=Count("id"))
        }
        post_trend_map = {
            item["created_at__date"]: item["count"]
            for item in Post.objects.filter(created_at__date__gte=recent_days[0])
            .values("created_at__date")
            .annotate(count=Count("id"))
        }
        destination_trend_map = {
            item["created_at__date"]: item["count"]
            for item in Destination.objects.filter(created_at__date__gte=recent_days[0])
            .values("created_at__date")
            .annotate(count=Count("id"))
        }

        recent_trends = [
            {
                "date": day.strftime("%Y-%m-%d"),
                "user_count": user_trend_map.get(day, 0),
                "post_count": post_trend_map.get(day, 0),
                "destination_count": destination_trend_map.get(day, 0),
            }
            for day in recent_days
        ]

        return Response(
            {
                "user_count": User.objects.count(),
                "post_count": Post.objects.count(),
                "destination_count": Destination.objects.count(),
                "comment_count": PostComment.objects.count(),
                "review_count": DestinationReview.objects.count(),
                "pending_post_count": Post.objects.filter(status="pending").count(),
                "pending_comment_count": PostComment.objects.filter(status="pending").count(),
                "timeline": timeline,
                "recent_trends": recent_trends,
            }
        )
