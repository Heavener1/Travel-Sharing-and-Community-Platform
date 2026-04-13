from django.contrib import admin

from apps.planner.models import TripPlan, TripStop


class TripStopInline(admin.TabularInline):
    model = TripStop
    extra = 0


@admin.register(TripPlan)
class TripPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "departure_city", "destination_city", "days", "budget", "created_at")
    inlines = [TripStopInline]
