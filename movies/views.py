from django.shortcuts import get_object_or_404, render

from .models import Movie


def home(request):
    return render(request, 'pages/home.html')


def movie_list(request):
    movies = Movie.objects.filter(is_active=True).only(
        'id',
        'title',
        'genre',
        'duration',
        'language',
        'poster',
    )
    return render(request, 'movies/movie_list.html', {'movies': movies})


def movie_detail(request, pk):
    movie = get_object_or_404(
        Movie.objects.filter(is_active=True),
        pk=pk,
    )
    return render(request, 'movies/movie_detail.html', {'movie': movie})
