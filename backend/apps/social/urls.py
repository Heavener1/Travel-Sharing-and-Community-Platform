from django.urls import path

from apps.social.views import (
    AdminDashboardView,
    CommentCreateView,
    LikeToggleView,
    PostDetailView,
    PostListCreateView,
)

urlpatterns = [
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("posts/", PostListCreateView.as_view(), name="post-list-create"),
    path("posts/<int:pk>/", PostDetailView.as_view(), name="post-detail"),
    path("posts/<int:post_id>/comments/", CommentCreateView.as_view(), name="comment-create"),
    path("posts/<int:post_id>/like/", LikeToggleView.as_view(), name="like-toggle"),
]
