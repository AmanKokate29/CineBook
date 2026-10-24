from django.urls import path

from .views import movie_showtimes, select_seats

app_name = 'theatres'

urlpatterns = [
    path('movies/<int:movie_id>/showtimes/', movie_showtimes, name='movie_showtimes'),
    path('shows/<int:show_id>/seats/', select_seats, name='select_seats'),
]
