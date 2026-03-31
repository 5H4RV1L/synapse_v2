from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatrooms_page, name='chatrooms'),
    path('create/', views.create_chatroom, name='create_chatroom'),
    path('room/<int:room_id>/', views.chatroom_detail, name='chatroom_detail'),
    path('room/<int:room_id>/join/', views.join_chatroom, name='join_chatroom'),
    path('room/<int:room_id>/join-invite/', views.join_via_invite, name='join_via_invite'),
    path('room/<int:room_id>/leave/', views.leave_chatroom, name='leave_chatroom'),
    path('room/<int:room_id>/invite/', views.invite_to_chatroom, name='invite_to_chatroom'),
    path('room/<int:room_id>/messages/', views.get_room_messages, name='get_room_messages'),
    path('room/<int:room_id>/send/', views.send_room_message, name='send_room_message'),
    path('search/', views.search_chatrooms, name='search_chatrooms'),
]