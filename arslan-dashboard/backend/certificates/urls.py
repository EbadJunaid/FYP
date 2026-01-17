# backend/certificates/urls.py
from django.urls import path
from .views import (
    hello_mongo_view,
    GlobalHealthView,
    CertificateListView,
    CertificateDetailView,
    CertificateDownloadView,
    UniqueFiltersView,
    EncryptionStrengthView,
    ValidityTrendsView,
    CAAnalyticsView,
    CAStatsView,
    ValidationDistributionView as CAValidationDistributionView,
    IssuerValidationMatrixView,
    GeographicDistributionView,
    FutureRiskView,
    VulnerabilitiesView,
    NotificationView,
    ValidityStatsView,
    ValidityDistributionView,
    IssuanceTimelineView,
    # Signature and Hashes page views
    SignatureStatsView,
    HashTrendsView,
    IssuerAlgorithmMatrixView,
    CertificateExportView,
    # SAN Analytics page views
    SANStatsView,
    SANDistributionView,
    SANTLDBreakdownView,
    SANWildcardBreakdownView,
)

urlpatterns = [
    # Legacy endpoint
    path('hello/', hello_mongo_view, name='hello_mongo'),
    
    # Core Dashboard APIs
    path('dashboard/global-health/', GlobalHealthView.as_view(), name='global_health'),
    
    # Certificate CRUD APIs
    path('certificates/', CertificateListView.as_view(), name='certificate_list'),
    path('certificates/download/', CertificateDownloadView.as_view(), name='certificate_download'),
    path('certificates/export/', CertificateExportView.as_view(), name='certificate_export'),
    path('certificates/<str:cert_id>/', CertificateDetailView.as_view(), name='certificate_detail'),
    
    # Analytics APIs
    path('unique-filters/', UniqueFiltersView.as_view(), name='unique_filters'),
    path('encryption-strength/', EncryptionStrengthView.as_view(), name='encryption_strength'),
    path('validity-trends/', ValidityTrendsView.as_view(), name='validity_trends'),
    path('ca-analytics/', CAAnalyticsView.as_view(), name='ca_analytics'),
    path('ca-stats/', CAStatsView.as_view(), name='ca_stats'),
    path('validation-distribution/', CAValidationDistributionView.as_view(), name='ca_validation_distribution'),
    path('issuer-validation-matrix/', IssuerValidationMatrixView.as_view(), name='issuer_validation_matrix'),
    path('geographic-distribution/', GeographicDistributionView.as_view(), name='geographic_distribution'),
    path('future-risk/', FutureRiskView.as_view(), name='future_risk'),
    path('vulnerabilities/', VulnerabilitiesView.as_view(), name='vulnerabilities'),
    
    # Validity Analysis APIs
    path('validity-stats/', ValidityStatsView.as_view(), name='validity_stats'),
    path('validity-distribution/', ValidityDistributionView.as_view(), name='validity_distribution'),
    path('issuance-timeline/', IssuanceTimelineView.as_view(), name='issuance_timeline'),
    
    # Signature and Hashes APIs
    path('signature-stats/', SignatureStatsView.as_view(), name='signature_stats'),
    path('hash-trends/', HashTrendsView.as_view(), name='hash_trends'),
    path('issuer-algorithm-matrix/', IssuerAlgorithmMatrixView.as_view(), name='issuer_algorithm_matrix'),
    
    # SAN Analytics APIs
    path('san-stats/', SANStatsView.as_view(), name='san_stats'),
    path('san-distribution/', SANDistributionView.as_view(), name='san_distribution'),
    path('san-tld-breakdown/', SANTLDBreakdownView.as_view(), name='san_tld_breakdown'),
    path('san-wildcard-breakdown/', SANWildcardBreakdownView.as_view(), name='san_wildcard_breakdown'),
    
    # Notifications API
    path('notifications/', NotificationView.as_view(), name='notifications'),
]