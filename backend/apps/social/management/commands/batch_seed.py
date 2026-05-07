import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.common.utils import track_destination_action
from apps.social.models import Post
from apps.social.views import (
    POST_CONTENT_TEMPLATES,
    POST_TAG_LIBRARY,
    POST_TITLE_TEMPLATES,
    SCENIC_SEED_LIBRARY,
)
from apps.travel.models import Destination
from apps.users.utils import get_user_display_name


class Command(BaseCommand):
    help = "批量生成测试数据：账号、景点或帖子"

    def add_arguments(self, parser):
        parser.add_argument("--type", type=str, required=True, choices=["accounts", "destinations", "posts"])
        parser.add_argument("--count", type=int, default=10)
        parser.add_argument("--start-number", type=int, default=1000)

    @transaction.atomic
    def handle(self, *args, **options):
        task_type = options["type"]
        count = max(1, min(options["count"], 200))

        if task_type == "accounts":
            self._create_accounts(count, options["start_number"])
        elif task_type == "destinations":
            self._create_destinations(count)
        elif task_type == "posts":
            self._create_posts(count)

    def _create_accounts(self, count, start_number):
        created = []
        current = start_number
        while len(created) < count:
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
            created.append({"username": username, "password": username})
        self.stdout.write(self.style.SUCCESS(f"已生成 {len(created)} 个测试账号。"))

    def _create_destinations(self, count):
        existing_count = Destination.objects.count()
        for index in range(count):
            base = random.choice(SCENIC_SEED_LIBRARY)
            sequence = existing_count + index + 1
            Destination.objects.create(
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
        self.stdout.write(self.style.SUCCESS(f"已生成 {count} 条景点数据。"))

    def _create_posts(self, count):
        users = list(User.objects.filter(is_active=True))
        destinations = list(Destination.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR("当前没有可用于发帖的用户。"))
            return
        if not destinations:
            self.stdout.write(self.style.ERROR("当前没有景点数据。"))
            return

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
        self.stdout.write(self.style.SUCCESS(f"已生成 {count} 篇帖子。"))
