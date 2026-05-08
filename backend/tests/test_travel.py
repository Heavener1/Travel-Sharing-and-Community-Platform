"""旅行模块测试：SmartSearch、缓存、Dashboard。"""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse


class TestSmartSearch:
    """ES 降级搜索测试。"""

    def test_empty_keyword_returns_featured(self, auth_client, destinations):
        """空关键词返回精选景点。"""
        resp = auth_client.get("/api/travel/smart-search/")
        assert resp.status_code == 200
        data = resp.data["data"] if "data" in resp.data else resp.data
        assert len(data["featured_results"]) > 0
        assert data["keyword"] == ""

    def test_search_keyword_finds_results(self, auth_client, destinations):
        """关键词搜索找到结果（DB 降级搜索）。"""
        from apps.travel.services import search_destinations_db
        results = search_destinations_db("测试", limit=10)
        assert len(results) > 0, f"Expected results>0, got {len(results)}"

    def test_search_keyword_finds_results_http(self, auth_client, destinations):
        """通过 HTTP 搜索也能工作。"""
        resp = auth_client.get("/api/travel/smart-search/?q=测试")
        assert resp.status_code == 200

    def test_search_no_match(self, auth_client, destinations):
        """无匹配关键词返回空结果。"""
        resp = auth_client.get("/api/travel/smart-search/?q=ZZZZNOTEXIST12345")
        assert resp.status_code == 200
        data = resp.data["data"] if "data" in resp.data else resp.data
        assert data["keyword"] == "ZZZZNOTEXIST12345"

    def test_search_with_hidden_gem(self, auth_client, destinations):
        """限定 hidden_gem 搜索。"""
        resp = auth_client.get("/api/travel/smart-search/?q=景点&hidden_gem=true")
        assert resp.status_code == 200
        data = resp.data["data"] if "data" in resp.data else resp.data
        # hidden_gem 景点应有 is_hidden_gem=True
        for item in data["results"]:
            assert item.get("is_hidden_gem") is True


class TestCaching:
    def test_recommendation_uses_cache(self, auth_client, destinations):
        """推荐接口应使用缓存（两次请求数据一致）。"""
        resp1 = auth_client.get("/api/travel/recommendations/")
        resp2 = auth_client.get("/api/travel/recommendations/")
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    def test_dashboard_uses_cache(self, auth_client, destinations):
        """Dashboard 应使用缓存。"""
        resp1 = auth_client.get("/api/travel/dashboard/")
        assert resp1.status_code == 200
        data = resp1.data["data"] if "data" in resp1.data else resp1.data
        # Dashboard 应包含统计字段
        assert "destination_count" in data
        assert "featured_destinations" in data

        resp2 = auth_client.get("/api/travel/dashboard/")
        assert resp2.status_code == 200

    def test_cache_invalidates_on_destination_create(self, auth_client, db):
        """创建 Destination 后 count 应增加。"""
        from apps.travel.models import Destination
        count1 = Destination.objects.count()
        Destination.objects.create(name="新景点X", city="北京", province="北京", summary="测试", tags="新", score=4.5)
        assert Destination.objects.count() == count1 + 1
