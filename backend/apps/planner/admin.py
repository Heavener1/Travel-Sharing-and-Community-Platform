from django.contrib import admin

from apps.planner.models import TripPlan, TripStop


class TripStopInline(admin.TabularInline):
    model = TripStop
    extra = 0
    raw_id_fields = ("destination",)


@admin.register(TripPlan)
class TripPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "departure_city", "destination_city", "days", "budget", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "user__username", "destination_city")
    raw_id_fields = ("user",)
    inlines = (TripStopInline,)
    ordering = ("-created_at",)


@admin.register(TripStop)
class TripStopAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "destination", "day_number", "sequence")
    raw_id_fields = ("trip", "destination")
    ordering = ("trip", "day_number", "sequence")
