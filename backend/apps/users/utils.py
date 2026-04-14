def get_user_display_name(user):
    if not user:
        return ""
    profile = getattr(user, "profile", None)
    nickname = (getattr(profile, "nickname", "") or "").strip()
    if nickname:
        return nickname
    first_name = (getattr(user, "first_name", "") or "").strip()
    if first_name:
        return first_name
    email = (getattr(user, "email", "") or "").strip()
    if email:
        return email
    return (getattr(user, "username", "") or "").strip()
