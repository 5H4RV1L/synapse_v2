from django.urls import path
from . import views

urlpatterns = [
    path('clear/', views.clear_notifications, name='clear_notifications'),
    path('api/', views.notifications_api, name='notifications_api'),
]