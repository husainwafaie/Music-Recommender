from django.urls import path

from . import views

urlpatterns = [
    path('my-taste/', views.my_taste, name='my_taste'),
    path("", views.index, name="index"),
    path('register/', views.register_view, name='register_view'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path('home/', views.mainpage, name="home"),
    path('spotify-login/', views.spotify_login, name='spotify_login'),
    path('callback/', views.spotify_callback, name='spotify_callback'),
    path('top-songs/', views.top_songs, name='top_songs'),
    path('top-artists/', views.top_artists, name='top_artists'),
    path('mode/', views.light_dark_mode, name='mode'),
    path('top-albums', views.top_albums, name="top_albums")
]