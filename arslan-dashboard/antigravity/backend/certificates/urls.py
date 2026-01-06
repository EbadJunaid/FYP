# backend/certificates/urls.py
from django.urls import path
from .views import hello_mongo_view

urlpatterns = [
    path('hello/', hello_mongo_view, name='hello_mongo'),
]