"""
缓存装饰器 — 基于 Django Redis 缓存的通用装饰器。
用法：@cache_result(timeout=300, prefix="dashboard")
"""
import functools
import hashlib
import json
import logging

from django.core.cache import cache

logger = logging.getLogger("apps.cache")


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """生成缓存键：prefix:hash(args+kwargs)。"""
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()[:12]}"


def cache_result(timeout: int = 300, prefix: str = "api"):
    """缓存视图方法返回值的装饰器。

    timeout: 缓存秒数，默认 5 分钟。
    prefix:  键前缀，建议用接口名。
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = _make_cache_key(prefix, *args, **kwargs)
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT  %s", cache_key)
                return cached

            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            logger.debug("Cache SET  %s (ttl=%ds)", cache_key, timeout)
            return result

        return wrapper

    return decorator


def invalidate_prefix(prefix: str):
    """使指定前缀的所有缓存失效。注意：Redis 不支持 prefix* 批量删除，
    此方法记录警告，建议在数据修改后调用更精细的失效策略。"""
    logger.warning("cache_invalidate called for prefix=%s — use targeted invalidation", prefix)


# ── AI 摘要缓存 ──

import hashlib

AI_SUMMARY_TTL = 3600  # 1 小时


def _make_ai_cache_key(keyword: str, candidate_ids: list[int]) -> str:
    """生成 AI 摘要缓存键：ai_summary:{keyword}:{ids_hash}。"""
    ids_hash = hashlib.md5(",".join(map(str, sorted(candidate_ids))).encode()).hexdigest()[:8]
    return f"ai_summary:{keyword}:{ids_hash}"


def get_cached_ai_summary(keyword: str, candidate_ids: list[int]) -> str | None:
    """获取缓存的 AI 摘要，无缓存返回 None。"""
    return cache.get(_make_ai_cache_key(keyword, candidate_ids))


def set_cached_ai_summary(keyword: str, candidate_ids: list[int], summary: str):
    """缓存 AI 摘要。"""
    cache.set(_make_ai_cache_key(keyword, candidate_ids), summary, AI_SUMMARY_TTL)
