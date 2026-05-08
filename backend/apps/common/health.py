"""健康检查端点 — 检查 DB / Redis / ES / MinIO 连通性。"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

logger = logging.getLogger("apps.health")


def _check_db():
    try:
        connections["default"].cursor()
        return "ok"
    except OperationalError as e:
        return str(e)[:120]


def _check_redis():
    try:
        cache.set("health_check", "1", timeout=5)
        return "ok" if cache.get("health_check") == "1" else "write/read mismatch"
    except Exception as e:
        return str(e)[:120]


def _check_es():
    if not getattr(settings, "ELASTICSEARCH_ENABLED", True):
        return "disabled"
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch(settings.ELASTICSEARCH_URL, request_timeout=3)
        return "ok" if es.ping() else "ping failed"
    except Exception as e:
        return str(e)[:120]


def _check_minio():
    try:
        from minio import Minio
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        client.list_buckets()
        return "ok"
    except Exception as e:
        return str(e)[:120]


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    checks = {
        "database": _check_db(),
        "redis": _check_redis(),
        "elasticsearch": _check_es(),
        "minio": _check_minio(),
    }
    all_ok = all(v == "ok" or v == "disabled" for v in checks.values())
    status_code = 200 if all_ok else 503
    return Response(
        {"status": "healthy" if all_ok else "degraded", "checks": checks},
        status=status_code,
    )
