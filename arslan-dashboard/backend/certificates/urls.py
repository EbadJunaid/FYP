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
    # COMMENT FOR NOTIFICATION ICON - Import
    # NotificationView,
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
    SANFilteredCertsView,
    # Trends Analytics page views
    TrendsStatsView,
    ExpirationForecastView,
    AlgorithmAdoptionView,
    ValidationLevelTrendsView,
    KeySizeTimelineView,
    # Shared Keys Analytics page views
    SharedKeyStatsView,
    SharedKeyDistributionView,
    SharedKeyByIssuerView,
    SharedKeyTimelineView,
    SharedKeyHeatmapView,
    SharedKeysListView,
    SharedKeyDetailView,
    # Database Management view functions
    get_current_database,
    get_available_databases,
    switch_database,
)

urlpatterns = [
    # Legacy endpoint
    path('hello/', hello_mongo_view, name='hello_mongo'),
    
    # Shared APIs in many pages...
    path('dashboard/global-health/', GlobalHealthView.as_view(), name='global_health'),
    path('validity-trends/', ValidityTrendsView.as_view(), name='validity_trends'),
    path('ca-analytics/', CAAnalyticsView.as_view(), name='ca_analytics'),
    path('geographic-distribution/', GeographicDistributionView.as_view(), name='geographic_distribution'),
    
    # Certificate CRUD APIs
    path('certificates/', CertificateListView.as_view(), name='certificate_list'),
    path('certificates/download/', CertificateDownloadView.as_view(), name='certificate_download'),
    path('certificates/export/', CertificateExportView.as_view(), name='certificate_export'),
    path('certificates/<str:cert_id>/', CertificateDetailView.as_view(), name='certificate_detail'),
   
    path('unique-filters/', UniqueFiltersView.as_view(), name='unique_filters'),
    path('validation-distribution/', CAValidationDistributionView.as_view(), name='ca_validation_distribution'),
    path('vulnerabilities/', VulnerabilitiesView.as_view(), name='vulnerabilities'),
   
    
    
    # Overview page APIs.. it also use 4 more apis "api/validity-trends/","api/ca-analytics/","api/geographic-distribution","api/dashboard/global-health/" these are shared with other pages..
    path('encryption-strength/', EncryptionStrengthView.as_view(), name='encryption_strength'),
    path('future-risk/', FutureRiskView.as_view(), name='future_risk'),
   
    # Database Management APIs
    path('databases/current/', get_current_database, name='current_database'),
    path('databases/available/', get_available_databases, name='available_databases'),
    path('databases/switch/', switch_database, name='switch_database'),
   
    # CA analysis page apis.. it also use one move api "api/ca-analytics" but that is shared with other pages tooo

    path('ca-stats/', CAStatsView.as_view(), name='ca_stats'),
    path('issuer-validation-matrix/', IssuerValidationMatrixView.as_view(), name='issuer_validation_matrix'),
   
    # Validity Analysis page APIs.. it also use 2 more apis "api/validity-trends/" and "api/dashboard/global-health/" they are shared with other pages too

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
    path('san-filtered-certs/', SANFilteredCertsView.as_view(), name='san_filtered_certs'), #this is same as api/certificate/.. but with one extra thing.. san count..
    
    # Trends Analytics APIs
    path('trends/stats/', TrendsStatsView.as_view(), name='trends_stats'),
    path('trends/expiration-forecast/', ExpirationForecastView.as_view(), name='trends_expiration_forecast'),
    path('trends/algorithm-adoption/', AlgorithmAdoptionView.as_view(), name='trends_algorithm_adoption'),
    path('trends/validation-levels/', ValidationLevelTrendsView.as_view(), name='trends_validation_levels'),
    path('trends/key-size-timeline/', KeySizeTimelineView.as_view(), name='trends_key_size_timeline'),
    
    # Shared Keys Analytics APIs
    path('shared-keys/stats/', SharedKeyStatsView.as_view(), name='shared_key_stats'),
    path('shared-keys/distribution/', SharedKeyDistributionView.as_view(), name='shared_key_distribution'),
    path('shared-keys/by-issuer/', SharedKeyByIssuerView.as_view(), name='shared_key_by_issuer'),
   
    # dont know why this shared-keys/timeline is present what is the role of it... but i have added it as well

    path('shared-keys/timeline/', SharedKeyTimelineView.as_view(), name='shared_key_timeline'),
    path('shared-keys/heatmap/', SharedKeyHeatmapView.as_view(), name='shared_key_heatmap'),
    path('shared-keys/list/', SharedKeysListView.as_view(), name='shared_keys_list'),
    path('shared-keys/detail/<str:public_key_hash>/', SharedKeyDetailView.as_view(), name='shared_key_detail'),
    
    # ============================================================
    # COMMENT FOR NOTIFICATION ICON - Backend URL
    # ============================================================
    # Notifications API
    # path('notifications/', NotificationView.as_view(), name='notifications'),
    
]
