from django.urls import path
from . import views

urlpatterns = [
    path('', views.search_profile, name='search_profile'),
    path('search/', views.search_page, name='search_page'),
    path('change-theme/', views.change_theme, name='change_theme'),
    path('settings/', views.settings_page, name='settings_page'),
    path('toggle-theme/', views.toggle_theme, name='toggle_theme'),
    path('set-theme/', views.set_theme, name='set_theme'),
    path('signup/', views.signup, name='signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('change-photo/', views.change_profile_photo, name='change_profile_photo'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('<str:username>/', views.profile, name='profile'),

]
