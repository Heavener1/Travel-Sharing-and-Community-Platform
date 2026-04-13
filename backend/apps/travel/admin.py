from django.contrib import admin

from apps.travel.models import Destination, DestinationReview, Hotel


class HotelInline(admin.TabularInline):
    model = Hotel
    extra = 0


class DestinationReviewInline(admin.TabularInline):
    model = DestinationReview
    extra = 0
    readonly_fields = ("user", "rating", "content", "created_at")


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "province", "score", "is_hidden_gem", "budget_level", "created_at")
    list_filter = ("province", "is_hidden_gem", "budget_level")
    search_fields = ("name", "city", "province", "tags")
    inlines = [HotelInline, DestinationReviewInline]


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ("name", "destination", "price_per_night", "rating")
    search_fields = ("name", "destination__name")


@admin.register(DestinationReview)
class DestinationReviewAdmin(admin.ModelAdmin):
    list_display = ("destination", "user", "rating", "created_at")
    search_fields = ("destination__name", "user__username", "content")
