from rest_framework import serializers

from apps.social.models import Notification, Post, PostComment
from apps.travel.services import resolve_media_url
from apps.users.utils import get_user_display_name


class PostCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = PostComment
        fields = (
            "id",
            "author",
            "author_name",
            "author_avatar",
            "parent",
            "content",
            "status",
            "created_at",
            "replies",
        )
        read_only_fields = ("author", "status")

    def get_replies(self, obj):
        replies = obj.replies.filter(status="approved").select_related("author")
        return PostCommentSerializer(replies, many=True, context=self.context).data

    def get_author_avatar(self, obj):
        return resolve_media_url(getattr(getattr(obj.author, "profile", None), "avatar", ""))

    def get_author_name(self, obj):
        return get_user_display_name(obj.author)


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    current_user_liked = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    cover_reference = serializers.CharField(source="cover", read_only=True)
    comments = PostCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "author_name",
            "author_avatar",
            "destination",
            "destination_name",
            "title",
            "content",
            "cover",
            "cover_reference",
            "tags",
            "status",
            "review_note",
            "created_at",
            "like_count",
            "comment_count",
            "current_user_liked",
            "comments",
        )
        read_only_fields = ("author", "status", "review_note")

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_comment_count(self, obj):
        return obj.comments.filter(status="approved").count()

    def get_cover(self, obj):
        return resolve_media_url(obj.cover)

    def get_author_avatar(self, obj):
        return resolve_media_url(getattr(getattr(obj.author, "profile", None), "avatar", ""))

    def get_author_name(self, obj):
        return get_user_display_name(obj.author)

    def get_current_user_liked(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["comments"] = PostCommentSerializer(
            instance.comments.filter(parent__isnull=True, status="approved").select_related("author"),
            many=True,
            context=self.context,
        ).data
        return data


class PostListSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    current_user_liked = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "author_name",
            "author_avatar",
            "destination",
            "destination_name",
            "title",
            "cover",
            "tags",
            "status",
            "created_at",
            "like_count",
            "comment_count",
            "current_user_liked",
            "content_preview",
        )

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_comment_count(self, obj):
        return obj.comments.filter(status="approved").count()

    def get_cover(self, obj):
        return resolve_media_url(obj.cover)

    def get_author_avatar(self, obj):
        return resolve_media_url(getattr(getattr(obj.author, "profile", None), "avatar", ""))

    def get_author_name(self, obj):
        return get_user_display_name(obj.author)

    def get_current_user_liked(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()

    def get_content_preview(self, obj):
        text = (obj.content or "").strip()
        return text[:120] + ("..." if len(text) > 120 else "")


class PostCreateSerializer(serializers.ModelSerializer):
    cover = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Post
        fields = ("destination", "title", "content", "cover", "tags")

    def validate_cover(self, value):
        if not value:
            return ""
        if value.startswith("minio://"):
            return value
        raise serializers.ValidationError("帖子封面请先上传，再保存帖子。")


class PostUpdateSerializer(serializers.ModelSerializer):
    cover = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Post
        fields = ("destination", "title", "content", "cover", "tags")

    def validate_cover(self, value):
        if not value:
            return ""
        if value.startswith("minio://"):
            return value
        raise serializers.ValidationError("帖子封面请先上传，再重新发布。")


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    actor_avatar = serializers.SerializerMethodField()
    post_title = serializers.CharField(source="post.title", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "message",
            "is_read",
            "created_at",
            "post",
            "post_title",
            "comment",
            "actor",
            "actor_name",
            "actor_avatar",
        )

    def get_actor_avatar(self, obj):
        return resolve_media_url(getattr(getattr(obj.actor, "profile", None), "avatar", ""))

    def get_actor_name(self, obj):
        return get_user_display_name(obj.actor)
