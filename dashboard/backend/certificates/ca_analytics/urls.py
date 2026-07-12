from django.urls import path
from .views import (
    CAStatsView,
    IssuerValidationMatrixView,
    CARankingView)

urlpatterns = [
    path('ca-stats/', CAStatsView.as_view(), name='ca_stats'),
    path('issuer-validation-matrix/', IssuerValidationMatrixView.as_view(), name='issuer_validation_matrix'),
    path('ranking/', CARankingView.as_view(), name='ca_ranking'),
]
