from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import CaptchaView, LoginView, MeView, RegisterView, UserDashboardView

urlpatterns = [
    path("captcha/", CaptchaView.as_view(), name="captcha"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("dashboard/", UserDashboardView.as_view(), name="user-dashboard"),
]
