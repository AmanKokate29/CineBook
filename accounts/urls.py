from django.urls import path

from .views import CineBookLoginView, logout_view, profile, register

app_name = 'accounts'

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', CineBookLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile, name='profile'),
]
