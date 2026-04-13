from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.travel.models import Destination
from apps.travel.services import get_es_client, index_destination
from django.conf import settings


@receiver(post_save, sender=Destination)
def sync_destination_to_es(sender, instance, **kwargs):
    try:
        index_destination(instance)
    except Exception:
        pass


@receiver(post_delete, sender=Destination)
def remove_destination_from_es(sender, instance, **kwargs):
    try:
        get_es_client().delete(index=settings.ELASTICSEARCH_INDEX, id=instance.id, ignore=[404])
    except Exception:
        pass
