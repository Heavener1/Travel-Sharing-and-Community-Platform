from django.contrib.auth.models import User
from django.db import models

from apps.travel.models import Destination


class Post(models.Model):
    STATUS_CHOICES = (
        ("pending", "待审核"),
        ("approved", "已通过"),
        ("rejected", "已拒绝"),
    )

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    title = models.CharField(max_length=150)
    content = models.TextField()
    cover = models.URLField(blank=True)
    tags = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    review_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title


class PostComment(models.Model):
    STATUS_CHOICES = (
        ("pending", "待审核"),
        ("approved", "已通过"),
        ("rejected", "已拒绝"),
    )

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")


class FavoritePost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="favorites")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_posts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")
        ordering = ("-created_at",)


class Notification(models.Model):
    TYPE_CHOICES = (
        ("post_like", "帖子点赞"),
        ("post_comment", "帖子评论"),
        ("comment_reply", "评论回复"),
    )

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="triggered_notifications")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    comment = models.ForeignKey(
        PostComment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class UserAction(models.Model):
    ACTION_CHOICES = (
        ("view", "浏览"),
        ("like", "点赞"),
        ("plan", "加入行程"),
        ("review", "评价"),
        ("favorite", "收藏"),
        ("post", "发布帖子"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="travel_actions")
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="user_actions")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
