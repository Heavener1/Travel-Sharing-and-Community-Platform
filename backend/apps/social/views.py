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

class ModerationSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, _request):
        return Response(
            {
                "pending_posts": Post.objects.filter(status="pending").count(),
                "pending_comments": PostComment.objects.filter(status="pending").count(),
            }
        )


class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, _request):
        posts = Post.objects.order_by("created_at")
        bucket_map = defaultdict(lambda: {label: 0 for _, _, label in TIME_SEGMENTS})

        for post in posts:
            local_dt = timezone.localtime(post.created_at)
            day_label = local_dt.strftime("%Y-%m-%d")
            for start, end, label in TIME_SEGMENTS:
                if start <= local_dt.hour <= end:
                    bucket_map[day_label][label] += 1
                    break

        timeline = []
        for date_label in sorted(bucket_map.keys()):
            segments = [{"label": label, "count": bucket_map[date_label][label]} for _, _, label in TIME_SEGMENTS]
            timeline.append(
                {
                    "date": date_label,
                    "total": sum(item["count"] for item in segments),
                    "segments": segments,
                }
            )

        today = timezone.localdate()
        recent_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        user_trend_map = {
            item["date_joined__date"]: item["count"]
            for item in User.objects.filter(date_joined__date__gte=recent_days[0]).values("date_joined__date").annotate(count=Count("id"))
        }
        post_trend_map = {
            item["created_at__date"]: item["count"]
            for item in Post.objects.filter(created_at__date__gte=recent_days[0]).values("created_at__date").annotate(count=Count("id"))
        }
        destination_trend_map = {
            item["created_at__date"]: item["count"]
            for item in Destination.objects.filter(created_at__date__gte=recent_days[0]).values("created_at__date").annotate(count=Count("id"))
        }

        recent_trends = [
            {
                "date": day.strftime("%Y-%m-%d"),
                "user_count": user_trend_map.get(day, 0),
                "post_count": post_trend_map.get(day, 0),
                "destination_count": destination_trend_map.get(day, 0),
            }
            for day in recent_days
        ]

        # Combine Post counts into a single aggregate query
        post_stats = Post.objects.aggregate(
            total=Count("id"), pending=Count("id", filter=Q(status="pending"))
        )
        # Combine PostComment counts
        comment_stats = PostComment.objects.aggregate(
            total=Count("id"), pending=Count("id", filter=Q(status="pending"))
        )

        return Response(
            {
                "user_count": User.objects.count(),
                "post_count": post_stats["total"],
                "destination_count": Destination.objects.count(),
                "comment_count": comment_stats["total"],
                "review_count": DestinationReview.objects.count(),
                "pending_post_count": post_stats["pending"],
                "pending_comment_count": comment_stats["pending"],
                "timeline": timeline,
                "recent_trends": recent_trends,
            }
        )


class AdminBatchSeedView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @transaction.atomic
    def post(self, request):
        task_type = request.data.get("task_type")
        count = max(1, min(safe_int(request.data.get("count"), 10), 200))

        if task_type == "accounts":
            start_number = max(1000, safe_int(request.data.get("start_number"), 1000))
            created_users = []
            current = start_number
            while len(created_users) < count:
                username = str(current)
                current += 1
                if User.objects.filter(username=username).exists():
                    continue
                user = User.objects.create_user(
                    username=username,
                    password=username,
                    email=f"{username}@example.com",
                )
                user.first_name = f"用户{username}"
                user.save(update_fields=["first_name"])
                created_users.append({"username": username, "password": username})

            return Response(
                {
                    "task_type": task_type,
                    "created_count": len(created_users),
                    "items": created_users[:10],
                    "message": f"已生成 {len(created_users)} 个测试账号，账号密码一致。",
                },
                status=status.HTTP_201_CREATED,
            )

        if task_type == "destinations":
            created_items = []
            existing_count = Destination.objects.count()
            for index in range(count):
                base = random.choice(SCENIC_SEED_LIBRARY)
                sequence = existing_count + index + 1
                destination = Destination.objects.create(
                    name=f"{base['name']}{sequence}",
                    province=base["province"],
                    city=base["city"],
                    summary=base["summary"],
                    tags=base["tags"],
                    budget_level=random.choice(["经济", "中等", "舒适"]),
                    best_season=random.choice(["春季", "夏季", "秋季", "四季皆宜"]),
                    score=round(random.uniform(4.1, 4.9), 1),
                    ticket_price=random.randint(0, 280),
                    suggested_days=random.randint(1, 4),
                    is_hidden_gem=random.choice([False, False, True]),
                )
                created_items.append(
                    {
                        "id": destination.id,
                        "name": destination.name,
                        "city": destination.city,
                        "province": destination.province,
                    }
                )

            return Response(
                {
                    "task_type": task_type,
                    "created_count": len(created_items),
                    "items": created_items[:10],
                    "message": f"已推送 {len(created_items)} 条景点数据。",
                },
                status=status.HTTP_201_CREATED,
            )

        if task_type == "posts":
            users = list(User.objects.filter(is_active=True))
            destinations = list(Destination.objects.all())
            if not users:
                return Response({"detail": "当前没有可用于发帖的用户，请先生成账号。"}, status=status.HTTP_400_BAD_REQUEST)
            if not destinations:
                return Response({"detail": "当前没有景点数据，请先批量生成景点。"}, status=status.HTTP_400_BAD_REQUEST)

            created_posts = []
            for index in range(count):
                author = random.choice(users)
                destination = random.choice(destinations)
                title = random.choice(POST_TITLE_TEMPLATES).format(destination=destination.name)
                content = random.choice(POST_CONTENT_TEMPLATES).format(destination=destination.name)
                post = Post.objects.create(
                    author=author,
                    destination=destination,
                    title=f"{title} #{index + 1}",
                    content=content,
                    tags=random.choice(POST_TAG_LIBRARY),
                    status="approved",
                )
                track_destination_action(author, destination, "post")
                created_posts.append(
                    {
                        "id": post.id,
                        "title": post.title,
                        "author": get_user_display_name(author),
                        "destination": destination.name,
                    }
                )

            return Response(
                {
                    "task_type": task_type,
                    "created_count": len(created_posts),
                    "items": created_posts[:10],
                    "message": f"已批量生成 {len(created_posts)} 篇帖子，并随机绑定到现有用户。",
                },
                status=status.HTTP_201_CREATED,
            )

        return Response({"detail": "不支持的批量任务类型。"}, status=status.HTTP_400_BAD_REQUEST)
