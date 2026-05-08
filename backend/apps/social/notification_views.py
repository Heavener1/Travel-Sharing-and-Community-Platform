import random
from collections import defaultdict
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils import build_user_preference_profile, extract_tags, safe_int, track_destination_action
from apps.social.models import FavoritePost, Notification, Post, PostComment, PostLike, UserAction
from apps.social.serializers import (
    FavoritePostSerializer,
    NotificationSerializer,
    PostCommentSerializer,
    PostCreateSerializer,
    PostListSerializer,
    PostSerializer,
    PostUpdateSerializer,
)
from apps.travel.models import Destination, DestinationReview
from apps.travel.serializers import DestinationSerializer
from apps.users.utils import get_user_display_name


TIME_SEGMENTS = [
    (0, 5, "00:00-05:59"),
    (6, 11, "06:00-11:59"),
    (12, 17, "12:00-17:59"),
    (18, 23, "18:00-23:59"),
]

SCENIC_SEED_LIBRARY = [
    {
        "name": "西湖",
        "province": "浙江省",
        "city": "杭州市",
        "summary": "湖光山色与人文古迹交织，适合慢节奏漫游、拍照和夜游体验。",
        "tags": "湖景,城市漫游,摄影",
    },
    {
        "name": "黄山风景区",
        "province": "安徽省",
        "city": "黄山市",
        "summary": "以奇松、怪石、云海著称，适合登山爱好者与自然风光摄影。",
        "tags": "山岳,日出,徒步",
    },
    {
        "name": "鼓浪屿",
        "province": "福建省",
        "city": "厦门市",
        "summary": "海岛街巷与文艺建筑氛围浓厚，适合情侣和周末轻旅行。",
        "tags": "海岛,文艺,漫步",
    },
    {
        "name": "丽江古城",
        "province": "云南省",
        "city": "丽江市",
        "summary": "古城夜色、民俗文化与周边雪山景观相互映衬，适合深度体验。",
        "tags": "古城,夜游,民俗",
    },
    {
        "name": "青海湖",
        "province": "青海省",
        "city": "海北藏族自治州",
        "summary": "高原湖泊视野开阔，夏季花海与环湖骑行体验都很有代表性。",
        "tags": "湖泊,骑行,高原",
    },
    {
        "name": "张家界国家森林公园",
        "province": "湖南省",
        "city": "张家界市",
        "summary": "峰林奇观极具辨识度，适合自然景观爱好者和索道观景体验。",
        "tags": "峰林,索道,自然奇观",
    },
]

POST_TITLE_TEMPLATES = [
    "在{destination}度过的两天一夜，风景和节奏都刚刚好",
    "{destination}旅行记录：路线、花费和避坑建议",
    "第一次去{destination}，这份体验比攻略更真实",
    "如果你也想去{destination}，这篇笔记可以先收藏",
    "周末打卡{destination}，分享一次轻松又充实的旅程",
]

POST_CONTENT_TEMPLATES = [
    "这次去{destination}主要想放慢节奏，好好感受当地的景色和生活氛围。整体安排比较轻松，上午先逛核心景点，下午留给拍照和散步，晚上再找一家评价不错的小店吃饭。交通、花费和游玩节奏都比较适合第一次去的朋友。",
    "出发前我做了不少攻略，但真正到了{destination}以后，还是觉得现场感受更重要。建议大家提前留出机动时间，不要把行程排太满。景点之间的移动、拍照停留、餐饮排队都会比想象中花更多时间。",
    "{destination}给我的最大感受是层次感很强，既有适合打卡拍照的热门区域，也有可以慢慢逛的安静角落。如果预算有限，可以优先选择交通方便的线路，把时间留给最值得停留的景点和夜晚氛围。",
]

POST_TAG_LIBRARY = [
    "周末游,拍照,攻略",
    "自驾,避坑,路线",
    "美食,夜游,轻旅行",
    "徒步,风景,体验",
]


def create_notification(*, recipient, actor, notification_type, message, post=None, comment=None):
    if not recipient or not actor or recipient == actor:
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        message=message,
        post=post,
        comment=comment,
    )

class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user).select_related("actor__profile", "post", "comment")[:30]
        serializer = NotificationSerializer(queryset, many=True, context={"request": request})
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"results": serializer.data, "unread_count": unread_count})


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"unread_count": 0})

