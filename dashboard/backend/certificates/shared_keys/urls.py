

from django.urls import path
from .views import (
    SharedKeyStatsView,
    SharedKeyDistributionView,
    SharedKeyByIssuerView,
    SharedKeyTimelineView,
    SharedKeyHeatmapView,
    SharedKeysListView,
    SharedKeyDetailView
)

urlpatterns = [
    path('stats/', SharedKeyStatsView.as_view(), name='shared_key_stats'),
    path('distribution/', SharedKeyDistributionView.as_view(), name='shared_key_distribution'),
    path('by-issuer/', SharedKeyByIssuerView.as_view(), name='shared_key_by_issuer'),
   
    # dont know why this shared-keys/timeline is present what is the role of it... but i have added it as well

    path('timeline/', SharedKeyTimelineView.as_view(), name='shared_key_timeline'),
    path('heatmap/', SharedKeyHeatmapView.as_view(), name='shared_key_heatmap'),
    path('list/', SharedKeysListView.as_view(), name='shared_keys_list'),
    path('detail/<str:public_key_hash>/', SharedKeyDetailView.as_view(), name='shared_key_detail'),
]