from django.core.management.base import BaseCommand

from apps.travel.services import ensure_bucket, rebuild_destination_index


class Command(BaseCommand):
    help = "初始化 MinIO bucket 和 ElasticSearch 索引"

    def handle(self, *args, **options):
        ensure_bucket()
        self.stdout.write(self.style.SUCCESS("MinIO bucket 已确认。"))
        rebuild_destination_index()
        self.stdout.write(self.style.SUCCESS("ElasticSearch 索引已重建。"))
