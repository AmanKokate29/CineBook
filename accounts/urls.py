from django.urls import path

from .views import login, profile

app_name = 'accounts'

urlpatterns = [
    path('login/', login, name='login'),
    path('profile/', profile, name='profile'),
]
