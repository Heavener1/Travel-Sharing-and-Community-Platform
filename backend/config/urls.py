from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.common.health import health_check


@api_view(["GET"])
def api_root(_request):
    return Response({"message": "旅游分享与交流平台 API 正常运行"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api_root),
    path("api/health/", health_check),
    path("api/auth/", include("apps.users.urls")),
    path("api/travel/", include("apps.travel.urls")),
    path("api/social/", include("apps.social.urls")),
    path("api/planner/", include("apps.planner.urls")),
    path("api/ai/", include("apps.ai.urls")),
]
