from django.contrib import admin

from apps.social.models import Post, PostComment, PostLike, UserAction


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "destination", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "content", "author__username")


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "parent", "status", "created_at")
    list_filter = ("status",)


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")


@admin.register(UserAction)
class UserActionAdmin(admin.ModelAdmin):
    list_display = ("user", "destination", "action_type", "created_at")
    list_filter = ("action_type",)
