from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from apps.users.models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "用户档案"


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ("id", "username", "email", "is_staff", "date_joined")
    search_fields = ("username", "email")


# 重新注册 User（因为 User 已由 django.contrib.auth 注册）
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "travel_level", "gender")
    list_filter = ("travel_level", "gender")
    search_fields = ("user__username", "nickname", "bio")
    raw_id_fields = ("user",)
