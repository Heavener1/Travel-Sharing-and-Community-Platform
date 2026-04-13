from django.contrib.auth.models import User
from django.db import models


class Destination(models.Model):
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80)
    province = models.CharField(max_length=80)
    cover = models.URLField(blank=True)
    summary = models.TextField()
    tags = models.CharField(max_length=200, blank=True)
    budget_level = models.CharField(max_length=20, default="中等")
    best_season = models.CharField(max_length=50, blank=True)
    score = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    is_hidden_gem = models.BooleanField(default=False)
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    suggested_days = models.PositiveIntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-score", "name")

    def __str__(self):
        return self.name


class DestinationReview(models.Model):
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="destination_reviews")
    rating = models.PositiveSmallIntegerField()
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("destination", "user"), name="unique_destination_review_per_user"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.destination.name} ({self.rating})"


class Hotel(models.Model):
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="hotels")
    name = models.CharField(max_length=120)
    cover = models.URLField(blank=True)
    address = models.CharField(max_length=200)
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    highlights = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("price_per_night", "-rating")

    def __str__(self):
        return self.name
