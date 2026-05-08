from django.contrib import admin

from apps.travel.models import Destination, DestinationReview, FavoriteDestination, Hotel


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "city", "province", "score", "is_hidden_gem", "budget_level")
    list_filter = ("is_hidden_gem", "budget_level", "best_season", "province")
    search_fields = ("name", "city", "province", "tags", "summary")
    list_editable = ("is_hidden_gem",)
    ordering = ("-score",)


@admin.register(DestinationReview)
class DestinationReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "destination", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("content", "destination__name", "user__username")
    raw_id_fields = ("destination", "user")
    ordering = ("-created_at",)


@admin.register(FavoriteDestination)
class FavoriteDestinationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "destination", "created_at")
    raw_id_fields = ("user", "destination")
    ordering = ("-created_at",)


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "destination", "price_per_night", "rating")
    search_fields = ("name", "destination__name")
    raw_id_fields = ("destination",)
    ordering = ("-rating",)
