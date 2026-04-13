from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.users.models import UserProfile


class Command(BaseCommand):
    help = "确保管理员账号存在"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="admin123456")
        parser.add_argument("--email", default="admin@example.com")

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username=options["username"],
            defaults={
                "email": options["email"],
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.email = options["email"]
        user.is_staff = True
        user.is_superuser = True
        user.set_password(options["password"])
        user.save()
        UserProfile.objects.get_or_create(user=user, defaults={"nickname": "系统管理员"})
        message = "管理员已创建" if created else "管理员已更新"
        self.stdout.write(self.style.SUCCESS(f"{message}: {options['username']}"))
