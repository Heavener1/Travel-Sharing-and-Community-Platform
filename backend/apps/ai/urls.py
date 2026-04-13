from django.urls import path

from apps.ai.views import (
    DestinationAnalysisStreamView,
    PostPolishStreamView,
    PostPolishView,
    ProviderListView,
    ScenicQAStreamView,
    ScenicQAView,
    TravelAssistantStreamView,
    TravelAssistantView,
)

urlpatterns = [
    path("providers/", ProviderListView.as_view(), name="ai-providers"),
    path("travel-assistant/", TravelAssistantView.as_view(), name="ai-travel-assistant"),
    path("travel-assistant/stream/", TravelAssistantStreamView.as_view(), name="ai-travel-assistant-stream"),
    path("destination-analysis/stream/", DestinationAnalysisStreamView.as_view(), name="ai-destination-analysis-stream"),
    path("polish-post/", PostPolishView.as_view(), name="ai-polish-post"),
    path("polish-post/stream/", PostPolishStreamView.as_view(), name="ai-polish-post-stream"),
    path("scenic-qa/", ScenicQAView.as_view(), name="ai-scenic-qa"),
    path("scenic-qa/stream/", ScenicQAStreamView.as_view(), name="ai-scenic-qa-stream"),
]
