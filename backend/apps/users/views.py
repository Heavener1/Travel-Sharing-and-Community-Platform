import base64
import io
import random
import string
import uuid

from django.contrib.auth.models import User
from django.core.cache import cache
from PIL import Image, ImageDraw, ImageFont
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.planner.models import TripPlan
from apps.planner.serializers import TripPlanSerializer
from apps.social.models import Post
from apps.social.serializers import PostSerializer
from apps.travel.models import DestinationReview
from apps.travel.serializers import DestinationReviewSerializer
from apps.users.models import UserProfile
from apps.users.serializers import LoginSerializer, ProfileUpdateSerializer, RegisterSerializer, UserSerializer


class CaptchaView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, _request):
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        captcha_key = uuid.uuid4().hex
        cache.set(f"captcha:{captcha_key}", code.lower(), timeout=300)

        image = Image.new("RGB", (120, 42), color=(250, 245, 238))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.text((18, 10), code, fill=(25, 50, 60), font=font)
        for _ in range(5):
            x1, y1 = random.randint(0, 120), random.randint(0, 42)
            x2, y2 = random.randint(0, 120), random.randint(0, 42)
            draw.line((x1, y1, x2, y2), fill=(193, 95, 44), width=1)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return Response({"captcha_key": captcha_key, "image": f"data:image/png;base64,{image_base64}"})


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            }
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.create_tokens())


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _serialized_user(user_id):
        user = User.objects.select_related("profile").get(pk=user_id)
        return UserSerializer(user).data

    def get(self, request):
        UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"nickname": ""},
        )
        return Response(self._serialized_user(request.user.id))

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"nickname": ""},
        )
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._serialized_user(request.user.id))


class UserDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        recent_posts = (
            Post.objects.filter(author=request.user)
            .select_related("destination", "author", "author__profile")
            .prefetch_related("comments", "likes")
            .order_by("-created_at")[:5]
        )
        recent_trips = (
            TripPlan.objects.filter(user=request.user)
            .prefetch_related("stops__destination")
            .order_by("-created_at")[:5]
        )
        recent_reviews = (
            DestinationReview.objects.filter(user=request.user)
            .select_related("destination", "user", "user__profile")
            .order_by("-created_at")[:5]
        )

        return Response(
            {
                "stats": {
                    "post_count": Post.objects.filter(author=request.user).count(),
                    "approved_post_count": Post.objects.filter(author=request.user, status="approved").count(),
                    "pending_post_count": Post.objects.filter(author=request.user, status="pending").count(),
                    "trip_count": TripPlan.objects.filter(user=request.user).count(),
                    "review_count": DestinationReview.objects.filter(user=request.user).count(),
                },
                "recent_posts": PostSerializer(
                    recent_posts,
                    many=True,
                    context={"request": request},
                ).data,
                "recent_trips": TripPlanSerializer(
                    recent_trips,
                    many=True,
                    context={"request": request},
                ).data,
                "recent_reviews": DestinationReviewSerializer(
                    recent_reviews,
                    many=True,
                    context={"request": request},
                ).data,
            }
        )
