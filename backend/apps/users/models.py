from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    GENDER_CHOICES = (
        ("male", "男"),
        ("female", "女"),
        ("other", "其他"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nickname = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    preferred_style = models.CharField(max_length=50, blank=True)
    avatar = models.CharField(max_length=255, blank=True)
    travel_level = models.CharField(max_length=30, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    birthday = models.DateField(null=True, blank=True)
    occupation = models.CharField(max_length=50, blank=True)
    signature = models.CharField(max_length=120, blank=True)
    homepage = models.URLField(blank=True)

    def __str__(self):
        return self.nickname or self.user.username
