from urllib.parse import quote

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.travel.services import resolve_media_url
from apps.users.models import UserProfile


def build_default_avatar(label):
    safe_label = (label or "旅友").strip()[:2] or "旅友"
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
      <rect width="160" height="160" rx="36" fill="#d96b2b"/>
      <circle cx="80" cy="58" r="28" fill="#fff4ea"/>
      <path d="M38 132c8-22 26-36 42-36s34 14 42 36" fill="#fff4ea"/>
      <text x="80" y="148" text-anchor="middle" font-size="20" fill="#fff4ea" font-family="Microsoft YaHei, sans-serif">{safe_label}</text>
    </svg>
    """.strip()
    return f"data:image/svg+xml;utf8,{quote(svg)}"


class UserProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    avatar_reference = serializers.CharField(source="avatar", read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "nickname",
            "bio",
            "city",
            "preferred_style",
            "avatar",
            "avatar_reference",
            "travel_level",
            "phone",
            "gender",
            "birthday",
            "occupation",
            "signature",
            "homepage",
        )

    def get_avatar(self, obj):
        return resolve_media_url(obj.avatar) or build_default_avatar(obj.nickname or obj.user.username)


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    avatar = serializers.SerializerMethodField()
    nickname = serializers.CharField(source="profile.nickname", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "email", "is_staff", "avatar", "nickname", "profile")

    def get_avatar(self, obj):
        avatar = getattr(getattr(obj, "profile", None), "avatar", "")
        nickname = getattr(getattr(obj, "profile", None), "nickname", "") or obj.username
        return resolve_media_url(avatar) or build_default_avatar(nickname)


class CaptchaValidationMixin:
    def validate_captcha(self, attrs):
        captcha_key = attrs.pop("captcha_key", "")
        captcha_code = attrs.pop("captcha_code", "")
        cached_code = cache.get(f"captcha:{captcha_key}")
        if not cached_code or str(cached_code).lower() != str(captcha_code).lower():
            raise serializers.ValidationError("图形验证码错误或已过期。")
        cache.delete(f"captcha:{captcha_key}")
        return attrs


class RegisterSerializer(CaptchaValidationMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    nickname = serializers.CharField(write_only=True, required=False, allow_blank=True)
    captcha_key = serializers.CharField(write_only=True)
    captcha_code = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "password", "email", "first_name", "nickname", "captcha_key", "captcha_code")

    def validate(self, attrs):
        return self.validate_captcha(attrs)

    def create(self, validated_data):
        nickname = validated_data.pop("nickname", "")
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user, nickname=nickname or user.username)
        return user


class LoginSerializer(CaptchaValidationMixin, serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    captcha_key = serializers.CharField(write_only=True)
    captcha_code = serializers.CharField(write_only=True)

    def validate(self, attrs):
        attrs = self.validate_captcha(attrs)
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("用户名或密码错误")
        attrs["user"] = user
        return attrs

    def create_tokens(self):
        user = self.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class ProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    nickname = serializers.CharField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    preferred_style = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.CharField(required=False, allow_blank=True)
    travel_level = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=UserProfile.GENDER_CHOICES, required=False, allow_blank=True)
    birthday = serializers.DateField(required=False, allow_null=True)
    occupation = serializers.CharField(required=False, allow_blank=True)
    signature = serializers.CharField(required=False, allow_blank=True)
    homepage = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = (
            "first_name",
            "nickname",
            "bio",
            "city",
            "preferred_style",
            "avatar",
            "travel_level",
            "phone",
            "gender",
            "birthday",
            "occupation",
            "signature",
            "homepage",
        )

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
            if data.get("birthday") == "":
                data["birthday"] = None
        return super().to_internal_value(data)

    def validate_avatar(self, value):
        if not value:
            return ""
        if value.startswith("minio://"):
            return value
        raise serializers.ValidationError("头像请先上传，再保存资料。")

    def validate_birthday(self, value):
        return value or None

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save()
        return instance
