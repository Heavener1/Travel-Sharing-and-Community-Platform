from django.urls import path

from apps.social.views import (
    AdminDashboardView,
    AdminBatchSeedView,
    CommentCreateView,
    FavoritePostListView,
    FavoritePostToggleView,
    LikeToggleView,
    NotificationListView,
    NotificationReadView,
    PostDetailView,
    PostListCreateView,
    PostRelatedView,
)

urlpatterns = [
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/batch-seed/", AdminBatchSeedView.as_view(), name="admin-batch-seed"),
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/read/", NotificationReadView.as_view(), name="notification-read"),
    path("posts/", PostListCreateView.as_view(), name="post-list-create"),
    path("favorites/posts/", FavoritePostListView.as_view(), name="favorite-post-list"),
    path("posts/<int:post_id>/favorite/", FavoritePostToggleView.as_view(), name="favorite-post-toggle"),
    path("posts/<int:post_id>/related/", PostRelatedView.as_view(), name="post-related"),
    path("posts/<int:pk>/", PostDetailView.as_view(), name="post-detail"),
    path("posts/<int:post_id>/comments/", CommentCreateView.as_view(), name="comment-create"),
    path("posts/<int:post_id>/like/", LikeToggleView.as_view(), name="like-toggle"),
]
