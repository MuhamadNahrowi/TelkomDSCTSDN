from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'apps'
urlpatterns = [
    path('', views.dashboard, name='dashboard')   
]