"""认证相关测试：登录、分页、限流。"""

import pytest
from django.urls import reverse


class TestAuth:
    def test_login_missing_fields(self, api_client, db):
        """登录缺少字段返回 400。"""
        resp = api_client.post(reverse("token_obtain_pair"), {})
        assert resp.status_code == 400

    def test_login_bad_credentials(self, api_client, test_user):
        """错误密码返回 401。"""
        resp = api_client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "wrongpassword"},
        )
        assert resp.status_code in (400, 401)

    def test_protected_endpoint_no_auth(self, api_client, db):
        """未认证也能访问公开接口（Dashboard 使用 AllowAny）。"""
        resp = api_client.get("/api/travel/destinations/")
        assert resp.status_code == 200

    def test_protected_endpoint_with_auth(self, auth_client):
        """认证后可访问受保护接口。"""
        resp = auth_client.get("/api/travel/dashboard/")
        assert resp.status_code == 200


class TestPagination:
    def test_page1_returns_10(self, auth_client, destinations):
        """第一页返回 10 条。"""
        resp = auth_client.get("/api/travel/destinations/?page=1")
        assert resp.status_code == 200
        data = resp.data["data"] if "data" in resp.data else resp.data
        results = data.get("results", data)
        assert len(results) == 10

    def test_page2_returns_remaining(self, auth_client, destinations):
        """第二页返回剩余 5 条。"""
        resp = auth_client.get("/api/travel/destinations/?page=2")
        assert resp.status_code == 200
        data = resp.data["data"] if "data" in resp.data else resp.data
        results = data.get("results", data)
        assert len(results) == 5

    def test_pagination_includes_next(self, auth_client, destinations):
        """分页响应包含 next 字段。"""
        resp = auth_client.get("/api/travel/destinations/?page=1")
        data = resp.data["data"] if "data" in resp.data else resp.data
        assert data.get("next") is not None


class TestRateLimiting:
    def test_anon_can_make_requests(self, api_client, db):
        """匿名用户可以在限流范围内多次请求。"""
        for _ in range(3):
            resp = api_client.get("/api/travel/destinations/")
            assert resp.status_code == 200
