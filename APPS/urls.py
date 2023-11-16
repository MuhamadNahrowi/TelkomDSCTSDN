from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'apps'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('getAllData', views.getAllData, name='getAllData'),
    path('getDataWord', views.getDataWord, name='getDataWord'),
    path('checkNewsData', views.checkNewsData, name='checkNewsData'),

]