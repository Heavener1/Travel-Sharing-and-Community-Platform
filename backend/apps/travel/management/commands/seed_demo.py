from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.planner.models import TripPlan, TripStop
from apps.social.models import Post, PostComment
from apps.travel.models import Destination, Hotel
from apps.users.models import UserProfile


DESTINATIONS = [
    {
        "name": "西湖",
        "city": "杭州",
        "province": "浙江",
        "cover": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80",
        "summary": "适合城市慢游、摄影打卡与夜景漫步，兼顾人文与自然。",
        "tags": "江南,湖景,摄影,美食",
        "budget_level": "中等",
        "best_season": "春秋",
        "score": 4.8,
        "is_hidden_gem": False,
        "ticket_price": 0,
        "suggested_days": 2,
    },
    {
        "name": "莫干山",
        "city": "湖州",
        "province": "浙江",
        "cover": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
        "summary": "民宿、竹海与山野步道结合，非常适合周末短逃离。",
        "tags": "山野,民宿,避暑,轻度徒步",
        "budget_level": "偏高",
        "best_season": "夏秋",
        "score": 4.7,
        "is_hidden_gem": True,
        "ticket_price": 120,
        "suggested_days": 2,
    },
    {
        "name": "平潭岛",
        "city": "福州",
        "province": "福建",
        "cover": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
        "summary": "海风、蓝眼泪与环岛公路很适合夏季自驾与情侣出游。",
        "tags": "海岛,自驾,情侣,日落",
        "budget_level": "中等",
        "best_season": "夏季",
        "score": 4.9,
        "is_hidden_gem": True,
        "ticket_price": 0,
        "suggested_days": 3,
    },
    {
        "name": "大理古城",
        "city": "大理",
        "province": "云南",
        "cover": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1200&q=80",
        "summary": "适合松弛感旅行，周边有洱海、喜洲与苍山线路。",
        "tags": "古城,慢生活,文艺,骑行",
        "budget_level": "中等",
        "best_season": "春秋",
        "score": 4.8,
        "is_hidden_gem": False,
        "ticket_price": 75,
        "suggested_days": 3,
    },
    {
        "name": "阿那亚",
        "city": "秦皇岛",
        "province": "河北",
        "cover": "https://images.unsplash.com/photo-1493558103817-58b2924bce98?auto=format&fit=crop&w=1200&q=80",
        "summary": "建筑感与海边度假氛围突出，适合周末拍照和疗愈。",
        "tags": "海边,建筑,周末,疗愈",
        "budget_level": "偏高",
        "best_season": "夏秋",
        "score": 4.6,
        "is_hidden_gem": True,
        "ticket_price": 0,
        "suggested_days": 2,
    },
]


class Command(BaseCommand):
    help = "创建旅游分享平台演示数据"

    def handle(self, *args, **options):
        demo_user, _ = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@example.com", "first_name": "演示用户"},
        )
        demo_user.set_password("demo123456")
        demo_user.save()
        UserProfile.objects.get_or_create(
            user=demo_user,
            defaults={
                "nickname": "漫游家阿德",
                "city": "上海",
                "preferred_style": "海岛,摄影,慢旅行",
                "bio": "喜欢把路线走慢一点，也把故事写深一点。",
                "travel_level": "资深背包客",
                "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80",
            },
        )

        created_destinations = []
        for item in DESTINATIONS:
            destination, _ = Destination.objects.get_or_create(name=item["name"], defaults=item)
            created_destinations.append(destination)
            Hotel.objects.get_or_create(
                destination=destination,
                name=f"{destination.name}漫旅酒店",
                defaults={
                    "cover": destination.cover,
                    "address": f"{destination.city}核心景区附近",
                    "price_per_night": 368,
                    "rating": 4.7,
                    "highlights": "交通便利,早餐丰富,适合拍照",
                },
            )

        first_post, _ = Post.objects.get_or_create(
            author=demo_user,
            title="平潭岛 3 天 2 晚轻松路线，适合第一次去海边的人",
            defaults={
                "destination": next(item for item in created_destinations if item.name == "平潭岛"),
                "content": "第一天看日落和蓝眼泪，第二天租车环岛，第三天留给海边咖啡馆和返程。整体预算不高，但非常出片。",
                "cover": "https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&w=1200&q=80",
                "tags": "海岛,攻略,自驾",
                "status": "approved",
            },
        )
        PostComment.objects.get_or_create(
            post=first_post,
            author=demo_user,
            content="如果怕晒，记得把环岛安排在下午四点以后。",
            defaults={"status": "approved"},
        )

        trip, _ = TripPlan.objects.get_or_create(
            user=demo_user,
            title="云南慢游 3 日计划",
            defaults={
                "departure_city": "上海",
                "days": 3,
                "budget": 4500,
                "preferences": "古城,慢生活,骑行",
            },
        )
        if not trip.stops.exists():
            destination = next(item for item in created_destinations if item.name == "大理古城")
            TripStop.objects.create(
                trip=trip,
                destination=destination,
                day_number=1,
                sequence=1,
                note="上午古城，下午洱海",
            )

        self.stdout.write(self.style.SUCCESS("演示数据已准备完成。默认账号：demo / demo123456"))
