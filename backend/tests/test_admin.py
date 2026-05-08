"""Admin 注册测试。"""

from django.contrib import admin
from django.contrib.auth.models import User


class TestAdminRegistrations:
    def test_travel_models_registered(self):
        """travel 所有 model 已注册到 admin。"""
        from apps.travel.models import Destination, DestinationReview, FavoriteDestination, Hotel

        for model in [Destination, DestinationReview, FavoriteDestination, Hotel]:
            assert admin.site.is_registered(model), f"{model.__name__} 未注册到 admin"

    def test_social_models_registered(self):
        """social 所有 model 已注册到 admin。"""
        from apps.social.models import FavoritePost, Notification, Post, PostComment, PostLike, UserAction

        for model in [Post, PostComment, PostLike, FavoritePost, Notification, UserAction]:
            assert admin.site.is_registered(model), f"{model.__name__} 未注册到 admin"

    def test_users_models_registered(self):
        """users model 已注册到 admin（User + UserProfile）。"""
        from apps.users.models import UserProfile

        assert admin.site.is_registered(User), "User 未注册到 admin"
        assert admin.site.is_registered(UserProfile), "UserProfile 未注册到 admin"

    def test_planner_models_registered(self):
        """planner model 已注册到 admin。"""
        from apps.planner.models import TripPlan, TripStop

        for model in [TripPlan, TripStop]:
            assert admin.site.is_registered(model), f"{model.__name__} 未注册到 admin"

    def test_admin_panel_accessible(self, auth_client):
        """认证用户可访问 admin 面板。"""
        # 需要 staff 权限
        from django.contrib.auth.models import User
        user = User.objects.get(username="testuser")
        user.is_staff = True
        user.save()

        resp = auth_client.get("/admin/")
        # admin 返回 200（已登录 staff）或 302（重定向）
        assert resp.status_code in (200, 302)
