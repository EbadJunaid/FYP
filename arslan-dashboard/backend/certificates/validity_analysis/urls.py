from django.urls import path
from .views import (
    IssuanceTimelineView,
    ValidityDistributionView,
    ValidityStatsView
)

urlpatterns = [
   path('validity-stats/', ValidityStatsView.as_view(), name='validity_stats'),
    path('validity-distribution/', ValidityDistributionView.as_view(), name='validity_distribution'),
    path('issuance-timeline/', IssuanceTimelineView.as_view(), name='issuance_timeline'),
    
]