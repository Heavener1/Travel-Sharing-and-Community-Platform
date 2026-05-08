from django.contrib import admin

from apps.social.models import FavoritePost, Notification, Post, PostComment, PostLike, UserAction


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "destination", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "content", "author__username", "destination__name")
    list_editable = ("status",)
    raw_id_fields = ("author", "destination")
    ordering = ("-created_at",)


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("content", "author__username")
    raw_id_fields = ("post", "author", "parent")
    ordering = ("-created_at",)


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    raw_id_fields = ("post", "user")
    ordering = ("-created_at",)


@admin.register(FavoritePost)
class FavoritePostAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post", "created_at")
    raw_id_fields = ("user", "post")
    ordering = ("-created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("message", "recipient__username")
    raw_id_fields = ("recipient", "actor", "post", "comment")
    ordering = ("-created_at",)


@admin.register(UserAction)
class UserActionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "destination", "action_type", "created_at")
    list_filter = ("action_type", "created_at")
    search_fields = ("user__username", "destination__name")
    raw_id_fields = ("user", "destination")
    ordering = ("-created_at",)
