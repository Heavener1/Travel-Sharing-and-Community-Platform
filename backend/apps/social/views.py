from collections import Counter, defaultdict
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.social.models import FavoritePost, Notification, Post, PostComment, PostLike, UserAction
from apps.social.serializers import (
    FavoritePostSerializer,
    NotificationSerializer,
    PostCommentSerializer,
    PostCreateSerializer,
    PostListSerializer,
    PostSerializer,
    PostUpdateSerializer,
)
from apps.travel.models import Destination, DestinationReview
from apps.travel.serializers import DestinationSerializer
from apps.users.utils import get_user_display_name


TIME_SEGMENTS = [
    (0, 5, "00:00-05:59"),
    (6, 11, "06:00-11:59"),
    (12, 17, "12:00-17:59"),
    (18, 23, "18:00-23:59"),
]


def extract_tags(raw_text):
    return [tag.strip() for tag in (raw_text or "").split(",") if tag.strip()]


def build_user_preference_profile(user):
    profile = {
        "tag_counter": Counter(),
        "city_counter": Counter(),
        "province_counter": Counter(),
        "destination_counter": Counter(),
    }
    if not user.is_authenticated:
        return profile

    action_weights = {
        "view": 1,
        "like": 3,
        "plan": 4,
        "review": 5,
        "favorite": 6,
        "post": 4,
    }

    actions = UserAction.objects.filter(user=user).select_related("destination")
    favorites = FavoritePost.objects.filter(user=user).select_related("post__destination")
    liked_posts = PostLike.objects.filter(user=user).select_related("post__destination")
    reviews = DestinationReview.objects.filter(user=user).select_related("destination")

    def absorb_destination(destination, weight):
        if not destination:
            return
        profile["destination_counter"][destination.id] += weight
        if destination.city:
            profile["city_counter"][destination.city] += weight
        if destination.province:
            profile["province_counter"][destination.province] += weight
        for tag in extract_tags(destination.tags):
            profile["tag_counter"][tag] += weight

    for action in actions:
        absorb_destination(action.destination, action_weights.get(action.action_type, 1))

    for favorite in favorites:
        absorb_destination(favorite.post.destination, 5)

    for like in liked_posts:
        absorb_destination(like.post.destination, 3)

    for review in reviews:
        absorb_destination(review.destination, 6 + int(review.rating))

    return profile


def create_notification(*, recipient, actor, notification_type, message, post=None, comment=None):
    if not recipient or not actor or recipient == actor:
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        message=message,
        post=post,
        comment=comment,
    )


def track_destination_action(user, destination, action_type):
    if user.is_authenticated and destination:
        UserAction.objects.create(user=user, destination=destination, action_type=action_type)


class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        queryset = Post.objects.select_related("author", "destination").prefetch_related("comments", "likes", "favorites")
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
        return PostListSerializer

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user, status="approved")
        track_destination_action(self.request.user, post.destination, "post")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        post = (
            Post.objects.select_related("author", "destination")
            .prefetch_related("comments", "likes", "favorites")
            .get(pk=serializer.instance.pk)
        )
        output = PostSerializer(post, context={"request": request}).data
        return Response(output, status=status.HTTP_201_CREATED)


class PostDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        queryset = (
            Post.objects.select_related("author", "destination")
            .prefetch_related("comments__author", "likes", "favorites")
        )
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

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        track_destination_action(request.user, instance.destination, "view")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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

        comment = serializer.save(author=self.request.user, post=post, status="approved")
        track_destination_action(self.request.user, post.destination, "view")

        if comment.parent_id:
            create_notification(
                recipient=comment.parent.author,
                actor=self.request.user,
                notification_type="comment_reply",
                message=f"{get_user_display_name(self.request.user)} 回复了你的评论",
                post=post,
                comment=comment,
            )
            if post.author_id != comment.parent.author_id:
                create_notification(
                    recipient=post.author,
                    actor=self.request.user,
                    notification_type="post_comment",
                    message=f"{get_user_display_name(self.request.user)} 在你的帖子下发布了新回复",
                    post=post,
                    comment=comment,
                )
            return

        create_notification(
            recipient=post.author,
            actor=self.request.user,
            notification_type="post_comment",
            message=f"{get_user_display_name(self.request.user)} 评论了你的帖子《{post.title}》",
            post=post,
            comment=comment,
        )


class LikeToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        post = Post.objects.get(pk=post_id)
        like, created = PostLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            return Response({"liked": False}, status=status.HTTP_200_OK)

        track_destination_action(request.user, post.destination, "like")
        create_notification(
            recipient=post.author,
            actor=request.user,
            notification_type="post_like",
            message=f"{get_user_display_name(request.user)} 点赞了你的帖子《{post.title}》",
            post=post,
        )
        return Response({"liked": True}, status=status.HTTP_201_CREATED)


class FavoritePostListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = FavoritePost.objects.filter(user=request.user).select_related("post__author", "post__destination")
        serializer = FavoritePostSerializer(queryset, many=True, context={"request": request})
        return Response({"results": serializer.data})


class FavoritePostToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        post = generics.get_object_or_404(Post, pk=post_id)
        favorite, created = FavoritePost.objects.get_or_create(post=post, user=request.user)
        if created:
            track_destination_action(request.user, post.destination, "favorite")
            return Response({"favorited": True}, status=status.HTTP_201_CREATED)
        favorite.delete()
        return Response({"favorited": False}, status=status.HTTP_200_OK)


class PostRelatedView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, post_id):
        current_post = generics.get_object_or_404(
            Post.objects.select_related("destination", "author"),
            pk=post_id,
        )
        post_tags = set(extract_tags(current_post.tags))
        title_chars = {char for char in (current_post.title or "") if char.strip()}
        profile = build_user_preference_profile(request.user)

        candidate_posts = (
            Post.objects.filter(status="approved")
            .exclude(pk=current_post.pk)
            .select_related("author", "destination")
            .prefetch_related("comments", "likes", "favorites")
        )
        scored_posts = []
        for item in candidate_posts:
            item_tags = set(extract_tags(item.tags))
            shared_tags = len(post_tags & item_tags)
            same_destination = 4 if current_post.destination_id and item.destination_id == current_post.destination_id else 0
            title_overlap = len(title_chars & {char for char in (item.title or "") if char.strip()}) * 0.08
            affinity = 0
            if item.destination:
                affinity += profile["destination_counter"].get(item.destination_id, 0) * 0.5
                affinity += profile["city_counter"].get(item.destination.city, 0) * 0.3
                affinity += profile["province_counter"].get(item.destination.province, 0) * 0.2
                affinity += sum(profile["tag_counter"].get(tag, 0) for tag in item_tags) * 0.18
            score = shared_tags * 2 + same_destination + title_overlap + item.likes.count() * 0.08 + item.comments.filter(status="approved").count() * 0.1 + affinity
            if score > 0:
                scored_posts.append((score, item))
        scored_posts.sort(key=lambda pair: pair[0], reverse=True)
        related_posts = [item for _, item in scored_posts[:12]]

        candidate_destinations = Destination.objects.prefetch_related("hotels", "reviews", "reviews__user__profile", "favorites").exclude(
            pk=current_post.destination_id
        )
        scored_destinations = []
        for item in candidate_destinations:
            item_tags = set(extract_tags(item.tags))
            shared_tags = len(post_tags & item_tags)
            current_destination_name = getattr(current_post.destination, "name", "")
            destination_boost = 3 if current_destination_name and item.name == current_destination_name else 0
            affinity = (
                profile["destination_counter"].get(item.id, 0) * 0.6
                + profile["city_counter"].get(item.city, 0) * 0.4
                + profile["province_counter"].get(item.province, 0) * 0.25
                + sum(profile["tag_counter"].get(tag, 0) for tag in item_tags) * 0.2
            )
            score = shared_tags * 1.8 + destination_boost + float(item.score) * 0.2 + affinity
            if score > 0:
                scored_destinations.append((score, item))
        scored_destinations.sort(key=lambda pair: pair[0], reverse=True)
        related_destinations = [item for _, item in scored_destinations[:9]]

        return Response(
            {
                "related_posts": PostListSerializer(related_posts, many=True, context={"request": request}).data,
                "related_destinations": DestinationSerializer(related_destinations, many=True, context={"request": request}).data,
            }
        )


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user).select_related("actor", "post", "comment")[:30]
        serializer = NotificationSerializer(queryset, many=True, context={"request": request})
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"results": serializer.data, "unread_count": unread_count})


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"unread_count": 0})


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
            segments = [{"label": label, "count": bucket_map[date_label][label]} for _, _, label in TIME_SEGMENTS]
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
            for item in User.objects.filter(date_joined__date__gte=recent_days[0]).values("date_joined__date").annotate(count=Count("id"))
        }
        post_trend_map = {
            item["created_at__date"]: item["count"]
            for item in Post.objects.filter(created_at__date__gte=recent_days[0]).values("created_at__date").annotate(count=Count("id"))
        }
        destination_trend_map = {
            item["created_at__date"]: item["count"]
            for item in Destination.objects.filter(created_at__date__gte=recent_days[0]).values("created_at__date").annotate(count=Count("id"))
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
