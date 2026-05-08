import os

# 在 Django setup 之前强制 SQLite
os.environ["DJANGO_DB_ENGINE"] = "sqlite"
os.environ.setdefault("DJANGO_REDIS_URL", "redis://127.0.0.1:6379/1")

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.travel.models import Destination


@pytest.fixture(autouse=True)
def _setup_django():
    """Ensure django.setup() is called (pytest-django handles this via DJANGO_SETTINGS_MODULE)."""
    pass


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def auth_client(db, test_user):
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client


@pytest.fixture
def destinations(db):
    """Create 15 test destinations."""
    items = []
    for i in range(1, 16):
        d = Destination.objects.create(
            name=f"测试景点{i}",
            city=f"城市{i % 5 + 1}",
            province=f"省份{i % 3 + 1}",
            summary=f"这是测试景点{i}的描述介绍",
            tags=f"标签{i},测试",
            score=4.0 + i * 0.05,
            is_hidden_gem=(i % 3 == 0),
        )
        items.append(d)
    return items
