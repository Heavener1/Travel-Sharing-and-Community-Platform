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
            defaults={"nickname": request.user.username},
        )
        return Response(self._serialized_user(request.user.id))

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"nickname": request.user.username},
        )
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._serialized_user(request.user.id))
