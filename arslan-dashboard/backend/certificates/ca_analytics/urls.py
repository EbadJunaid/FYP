from django.urls import path
from .views import CAStatsView, IssuerValidationMatrixView

urlpatterns = [
    path('ca-stats/', CAStatsView.as_view(), name='ca_stats'),
    path('issuer-validation-matrix/', IssuerValidationMatrixView.as_view(), name='issuer_validation_matrix'),
]