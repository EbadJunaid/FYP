from django.urls import path
from .views import (
    SANFilteredCertsView,
    SANWildcardBreakdownView,
    SANTLDBreakdownView,
    SANDistributionView,
    SANStatsView)

urlpatterns = [
    path('san-stats/', SANStatsView.as_view(), name='san_stats'),
    path('san-distribution/', SANDistributionView.as_view(), name='san_distribution'),
    path('san-tld-breakdown/', SANTLDBreakdownView.as_view(), name='san_tld_breakdown'),
    path('san-wildcard-breakdown/', SANWildcardBreakdownView.as_view(), name='san_wildcard_breakdown'),
    path('san-filtered-certs/', SANFilteredCertsView.as_view(), name='san_filtered_certs'), #this is same as api/certificate/.. but with one extra thing.. san count..
]