import json
from collections import Counter, defaultdict

from apps.social.models import FavoritePost, PostLike, UserAction
from apps.travel.models import DestinationReview


def extract_tags(raw_text):
    return [tag.strip() for tag in (raw_text or "").split(",") if tag.strip()]


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sse_event(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_user_preference_profile(user):
    profile = {
        "tag_counter": Counter(),
        "city_counter": Counter(),
        "province_counter": Counter(),
        "destination_counter": Counter(),
    }
    if not user.is_authenticated:
        return profile

    action_weights = {
        "view": 1,
        "like": 3,
        "plan": 4,
        "review": 5,
        "favorite": 6,
        "post": 4,
    }

    actions = UserAction.objects.filter(user=user).select_related("destination")
    favorites = FavoritePost.objects.filter(user=user).select_related("post__destination")
    liked_posts = PostLike.objects.filter(user=user).select_related("post__destination")
    reviews = DestinationReview.objects.filter(user=user).select_related("destination")

    def absorb_destination(destination, weight):
        if not destination:
            return
        profile["destination_counter"][destination.id] += weight
        if destination.city:
            profile["city_counter"][destination.city] += weight
        if destination.province:
            profile["province_counter"][destination.province] += weight
        for tag in extract_tags(destination.tags):
            profile["tag_counter"][tag] += weight

    for action in actions:
        absorb_destination(action.destination, action_weights.get(action.action_type, 1))

    for favorite in favorites:
        absorb_destination(favorite.post.destination, 5)

    for like in liked_posts:
        absorb_destination(like.post.destination, 3)

    for review in reviews:
        absorb_destination(review.destination, 6 + int(review.rating))

    return profile


def track_destination_action(user, destination, action_type):
    if user.is_authenticated and destination:
        UserAction.objects.create(user=user, destination=destination, action_type=action_type)
