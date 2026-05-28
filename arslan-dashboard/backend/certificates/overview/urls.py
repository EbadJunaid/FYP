from django.urls import path
from .views import (
    UniqueFiltersView,
    FutureRiskView,
    EncryptionStrengthView)

urlpatterns = [
    path('unique-filters/', UniqueFiltersView.as_view(), name='unique_filters'),
    path('future-risk/', FutureRiskView.as_view(), name='future_risk'),
    path('encryption-strength/', EncryptionStrengthView.as_view(), name='encryption_strength')
]
