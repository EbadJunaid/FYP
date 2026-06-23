from django.urls import path
from .views import (
    SignatureStatsView,
    HashTrendsView,
    IssuerAlgorithmMatrixView
)

urlpatterns = [
    path('signature-stats/', SignatureStatsView.as_view(), name='signature_stats'),
    path('hash-trends/', HashTrendsView.as_view(), name='hash_trends'),
    path('issuer-algorithm-matrix/', IssuerAlgorithmMatrixView.as_view(), name='issuer_algorithm_matrix'),
]
