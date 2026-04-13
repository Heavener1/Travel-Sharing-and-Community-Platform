from urllib.parse import quote

from django.db.models import Avg
from rest_framework import serializers

from apps.travel.models import Destination, DestinationReview, Hotel
from apps.travel.services import resolve_media_url
from apps.users.serializers import build_default_avatar


def build_default_destination_cover(name):
    safe_name = (name or "景点").strip()[:6] or "景点"
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="#f3c17a"/>
          <stop offset="50%" stop-color="#d96b2b"/>
          <stop offset="100%" stop-color="#2f6f73"/>
        </linearGradient>
      </defs>
      <rect width="1200" height="720" fill="url(#bg)"/>
      <circle cx="970" cy="150" r="72" fill="rgba(255,244,234,0.55)"/>
      <path d="M120 530 L360 270 L560 480 L720 320 L980 580 L120 580 Z" fill="rgba(255,244,234,0.24)"/>
      <path d="M150 580 C250 420 360 360 470 380 C610 405 710 520 860 520 C955 520 1030 490 1100 430 L1100 720 L150 720 Z" fill="rgba(255,244,234,0.3)"/>
      <text x="88" y="128" font-size="34" fill="#fff4ea" font-family="Microsoft YaHei, sans-serif" letter-spacing="6">SCENIC SPOT</text>
      <text x="88" y="610" font-size="72" fill="#fffdf9" font-family="Microsoft YaHei, sans-serif" font-weight="700">{safe_name}</text>
      <text x="88" y="662" font-size="28" fill="#fff4ea" font-family="Microsoft YaHei, sans-serif">等待旅行者补充精彩封面</text>
    </svg>
    """.strip()
    return f"data:image/svg+xml;utf8,{quote(svg)}"


def get_rating_distribution(destination):
    counts = {star: 0 for star in range(1, 6)}
    for review in destination.reviews.all():
        counts[review.rating] = counts.get(review.rating, 0) + 1
    return [{"star": star, "count": counts[star]} for star in range(5, 0, -1)]


class HotelSerializer(serializers.ModelSerializer):
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = "__all__"

    def get_cover(self, obj):
        return resolve_media_url(obj.cover) or build_default_destination_cover(obj.name)


class DestinationReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    nickname = serializers.CharField(source="user.profile.nickname", read_only=True)
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = DestinationReview
        fields = ("id", "rating", "content", "created_at", "username", "nickname", "author_avatar")

    def get_author_avatar(self, obj):
        avatar = getattr(getattr(obj.user, "profile", None), "avatar", "")
        nickname = getattr(getattr(obj.user, "profile", None), "nickname", "") or obj.user.username
        return resolve_media_url(avatar) or build_default_avatar(nickname)


class DestinationSerializer(serializers.ModelSerializer):
    hotels = HotelSerializer(many=True, read_only=True)
    tag_list = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = (
            "id",
            "name",
            "city",
            "province",
            "cover",
            "summary",
            "tags",
            "tag_list",
            "budget_level",
            "best_season",
            "score",
            "is_hidden_gem",
            "ticket_price",
            "suggested_days",
            "created_at",
            "hotels",
            "review_count",
            "average_rating",
        )

    def get_tag_list(self, obj):
        return [tag.strip() for tag in obj.tags.split(",") if tag.strip()]

    def get_cover(self, obj):
        return resolve_media_url(obj.cover) or build_default_destination_cover(obj.name)

    def get_review_count(self, obj):
        return obj.reviews.count() if hasattr(obj, "reviews") else 0

    def get_average_rating(self, obj):
        average = obj.reviews.aggregate(avg=Avg("rating")).get("avg") if hasattr(obj, "reviews") else None
        return round(float(average), 1) if average is not None else float(obj.score)


class DestinationCreateSerializer(serializers.ModelSerializer):
    cover = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Destination
        fields = (
            "name",
            "province",
            "city",
            "summary",
            "cover",
            "tags",
            "budget_level",
            "best_season",
            "ticket_price",
            "suggested_days",
            "is_hidden_gem",
        )


class DestinationReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinationReview
        fields = ("rating", "content")

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("评分必须在 1 到 5 星之间。")
        return value

    def validate(self, attrs):
        if attrs.get("content") and not attrs.get("rating"):
            raise serializers.ValidationError("评价内容必须和评分一起提交。")
        return attrs


class DestinationDetailSerializer(DestinationSerializer):
    rating_distribution = serializers.SerializerMethodField()
    reviews = DestinationReviewSerializer(many=True, read_only=True)
    current_user_review = serializers.SerializerMethodField()

    class Meta(DestinationSerializer.Meta):
        fields = DestinationSerializer.Meta.fields + (
            "rating_distribution",
            "reviews",
            "current_user_review",
        )

    def get_rating_distribution(self, obj):
        return get_rating_distribution(obj)

    def get_current_user_review(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        review = next((item for item in obj.reviews.all() if item.user_id == request.user.id), None)
        return DestinationReviewSerializer(review).data if review else None
