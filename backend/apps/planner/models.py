from django.contrib.auth.models import User
from django.db import models

from apps.travel.models import Destination


class TripPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trip_plans")
    title = models.CharField(max_length=120)
    departure_city = models.CharField(max_length=80)
    destination_city = models.CharField(max_length=80, blank=True)
    days = models.PositiveIntegerField(default=3)
    budget = models.PositiveIntegerField(default=3000)
    preferences = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title


class TripStop(models.Model):
    trip = models.ForeignKey(TripPlan, on_delete=models.CASCADE, related_name="stops")
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="trip_stops")
    day_number = models.PositiveIntegerField(default=1)
    sequence = models.PositiveIntegerField(default=1)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("day_number", "sequence")
