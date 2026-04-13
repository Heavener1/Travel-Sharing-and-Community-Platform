from django.apps import AppConfig


class TravelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.travel"
    label = "travel"

    def ready(self):
        from apps.travel import signals  # noqa: F401
