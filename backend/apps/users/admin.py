from django.contrib import admin

from apps.users.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "nickname", "city", "preferred_style", "travel_level")
    search_fields = ("user__username", "nickname", "city")
