from django.urls import path

from .views import movie_detail, movie_list

app_name = 'movies'

urlpatterns = [
    path('', movie_list, name='list'),
    path('<int:pk>/', movie_detail, name='detail'),
]
