from django.urls import path

from apps.planner.views import TripGeneratorView, TripPlanListCreateView

urlpatterns = [
    path("trips/", TripPlanListCreateView.as_view(), name="trip-list-create"),
    path("generate/", TripGeneratorView.as_view(), name="trip-generate"),
]

