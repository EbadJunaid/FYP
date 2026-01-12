# backend/certificates/urls.py
from django.urls import path
from .views import (
    hello_mongo_view,
    GlobalHealthView,
    CertificateListView,
    CertificateDetailView,
    UniqueFiltersView,
    EncryptionStrengthView,
    ValidityTrendsView,
    CAAnalyticsView,
    GeographicDistributionView,
    FutureRiskView,
    VulnerabilitiesView,
)

urlpatterns = [
    # Legacy endpoint
    path('hello/', hello_mongo_view, name='hello_mongo'),
    
    # Core Dashboard APIs
    path('dashboard/global-health/', GlobalHealthView.as_view(), name='global_health'),
    
    # Certificate CRUD APIs
    path('certificates/', CertificateListView.as_view(), name='certificate_list'),
    path('certificates/<str:cert_id>/', CertificateDetailView.as_view(), name='certificate_detail'),
    
    # Analytics APIs
    path('unique-filters/', UniqueFiltersView.as_view(), name='unique_filters'),
    path('encryption-strength/', EncryptionStrengthView.as_view(), name='encryption_strength'),
    path('validity-trends/', ValidityTrendsView.as_view(), name='validity_trends'),
    path('ca-analytics/', CAAnalyticsView.as_view(), name='ca_analytics'),
    path('geographic-distribution/', GeographicDistributionView.as_view(), name='geographic_distribution'),
    path('future-risk/', FutureRiskView.as_view(), name='future_risk'),
    path('vulnerabilities/', VulnerabilitiesView.as_view(), name='vulnerabilities'),
]