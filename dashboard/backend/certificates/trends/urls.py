from django.urls import path
from .views import (
    TrendsStatsView,
    ExpirationForecastView,
    AlgorithmAdoptionView,
    ValidationLevelTrendsView,
    KeySizeTimelineView
)

urlpatterns = [
    path('stats/', TrendsStatsView.as_view(), name='trends_stats'),
    path('expiration-forecast/', ExpirationForecastView.as_view(), name='trends_expiration_forecast'),
    path('algorithm-adoption/', AlgorithmAdoptionView.as_view(), name='trends_algorithm_adoption'),
    path('validation-levels/', ValidationLevelTrendsView.as_view(), name='trends_validation_levels'),
    path('key-size-timeline/', KeySizeTimelineView.as_view(), name='trends_key_size_timeline'),
    
]
