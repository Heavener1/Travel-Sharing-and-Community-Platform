from collections import defaultdict

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from apps.social.models import Post, PostComment, PostLike, UserAction
from apps.social.serializers import PostCommentSerializer, PostSerializer
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

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        if post.destination:
            UserAction.objects.create(user=self.request.user, destination=post.destination, action_type="view")


class PostDetailView(generics.RetrieveAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        queryset = Post.objects.select_related("author", "destination").prefetch_related("comments__author", "likes")
        if self.request.user.is_staff:
            return queryset
        if self.request.user.is_authenticated:
            return queryset.filter(Q(status="approved") | Q(author=self.request.user)).distinct()
        return queryset.filter(status="approved")


class CommentCreateView(generics.CreateAPIView):
    serializer_class = PostCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post = Post.objects.get(pk=self.kwargs["post_id"])
        if post.status != "approved" and not self.request.user.is_staff and post.author != self.request.user:
            raise permissions.PermissionDenied("该帖子尚未通过审核")
        serializer.save(author=self.request.user, post=post)


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
            }
        )
