from django.core.management.base import BaseCommand

from apps.travel.services import rebuild_destination_index


class Command(BaseCommand):
    help = "全量重建 Elasticsearch 索引（用于定时同步，确保 ES 与 MySQL 数据一致）"

    def handle(self, *args, **options):
        self.stdout.write("正在重建 ES 索引...")
        rebuild_destination_index()
        self.stdout.write(self.style.SUCCESS("Elasticsearch 索引重建完成。"))
