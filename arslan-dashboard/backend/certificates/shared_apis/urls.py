from django.urls import path
from .views import (
    CertificateDetailView,
    CertificateListView,
    CAAnalyticsView,
    GeographicDistributionView,
    ValidityTrendsView,
    GlobalHealthView
    )

urlpatterns = [
    path('global-health/', GlobalHealthView.as_view(), name='global_health'),
    path('validity-trends/', ValidityTrendsView.as_view(), name='validity_trends'),
    path('ca-analytics/', CAAnalyticsView.as_view(), name='ca_analytics'),
    path('geographic-distribution/', GeographicDistributionView.as_view(), name='geographic_distribution'),
    path('certificates/', CertificateListView.as_view(), name='certificate_list'),
    path('certificates/<str:cert_id>/', CertificateDetailView.as_view(), name='certificate_detail'),
    
    ]