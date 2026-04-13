from django.urls import path

from apps.travel.views import (
    DestinationDetailView,
    DestinationListView,
    DestinationReviewCreateView,
    HotelListView,
    RecommendationView,
    SmartSearchView,
    SmartSearchStreamView,
    TravelDashboardView,
    UploadImageView,
)

urlpatterns = [
    path("dashboard/", TravelDashboardView.as_view(), name="travel-dashboard"),
    path("destinations/", DestinationListView.as_view(), name="destination-list"),
    path("smart-search/", SmartSearchView.as_view(), name="smart-search"),
    path("smart-search/stream/", SmartSearchStreamView.as_view(), name="smart-search-stream"),
    path("destinations/<int:pk>/", DestinationDetailView.as_view(), name="destination-detail"),
    path("destinations/<int:pk>/reviews/", DestinationReviewCreateView.as_view(), name="destination-review-create"),
    path("hotels/", HotelListView.as_view(), name="hotel-list"),
    path("recommendations/", RecommendationView.as_view(), name="recommendation-list"),
    path("upload/", UploadImageView.as_view(), name="upload-image"),
]
