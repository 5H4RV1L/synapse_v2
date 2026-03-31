from django.urls import path
from . import views

urlpatterns = [
    path('', views.feed, name='feed'),
    path('create/', views.create_post_page, name='create_post_page'),
    path('delete/<int:post_id>/', views.delete_post, name='delete_post'),
    path('vote/<int:post_id>/<str:vote_type>/', views.vote_post, name='vote_post'),

]
