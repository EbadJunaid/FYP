from django.urls import path
from . import views

urlpatterns = [
    path('data/', views.overview_data, name='overview_data'),
    path('certificates/', views.certificate_list, name='certificate_list'),
    # path('certificate_warnings/',views.certificate_warnings,name='certificate_warning')
]
