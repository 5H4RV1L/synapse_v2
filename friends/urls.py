from django.urls import path
from . import views

urlpatterns = [
    path('send/<str:username>/', views.send_friend_request, name='send_friend_request'),
    path('accept/<int:request_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('decline/<int:request_id>/', views.decline_friend_request, name='decline_friend_request'),

]
