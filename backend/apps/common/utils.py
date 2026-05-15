"""
公共工具函数 — 标签解析、SSE 格式化、用户偏好画像构建、行为埋点。
"""

import json
from collections import Counter, defaultdict

from apps.social.models import FavoritePost, PostLike, UserAction
from apps.travel.models import DestinationReview


def extract_tags(raw_text):
    """将逗号分隔的字符串拆分为标签列表。"""
    return [tag.strip() for tag in (raw_text or "").split(",") if tag.strip()]


def safe_int(value, default=0):
    """安全整数转换，失败时返回默认值。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sse_event(event, data):
    """格式化为 SSE 标准字符串：event: xxx\\ndata: json\\n\\n"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_user_preference_profile(user):
    """构建用户偏好画像：综合 UserAction、FavoritePost、PostLike、DestinationReview
    四类行为数据，按加权规则统计 tags/city/province/destination 的偏好分数。"""
    profile = {
        "tag_counter": Counter(),
        "city_counter": Counter(),
        "province_counter": Counter(),
        "destination_counter": Counter(),
    }
    if not user.is_authenticated:
        return profile

    action_weights = {
        "view": 1,
        "like": 3,
        "plan": 4,
        "review": 5,
        "favorite": 6,
        "post": 4,
    }

    actions = UserAction.objects.filter(user=user).select_related("destination")
    favorites = FavoritePost.objects.filter(user=user).select_related("post__destination")
    liked_posts = PostLike.objects.filter(user=user).select_related("post__destination")
    reviews = DestinationReview.objects.filter(user=user).select_related("destination")

    def absorb_destination(destination, weight):
        if not destination:
            return
        profile["destination_counter"][destination.id] += weight
        if destination.city:
            profile["city_counter"][destination.city] += weight
        if destination.province:
            profile["province_counter"][destination.province] += weight
        for tag in extract_tags(destination.tags):
            profile["tag_counter"][tag] += weight

    for action in actions:
        absorb_destination(action.destination, action_weights.get(action.action_type, 1))

    for favorite in favorites:
        absorb_destination(favorite.post.destination, 5)

    for like in liked_posts:
        absorb_destination(like.post.destination, 3)

    for review in reviews:
        absorb_destination(review.destination, 6 + int(review.rating))

    return profile


def track_destination_action(user, destination, action_type):
    """记录用户对景点的操作行为，用于后续个性化推荐计算。"""
    if user.is_authenticated and destination:
        UserAction.objects.create(user=user, destination=destination, action_type=action_type)
