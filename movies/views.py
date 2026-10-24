from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Movie


MOVIES_PER_PAGE = 12
MAX_SEARCH_LENGTH = 100


def home(request):
    return render(request, 'pages/home.html')


def movie_list(request):
    movies = Movie.objects.filter(is_active=True)
    genres = list(
        movies.order_by()
        .values_list('genre', flat=True)
        .distinct()
        .order_by('genre')
    )

    search_query = request.GET.get('q', '').strip()[:MAX_SEARCH_LENGTH]
    requested_genre = request.GET.get('genre', '').strip()
    selected_genre = next(
        (genre for genre in genres if genre.casefold() == requested_genre.casefold()),
        '',
    )

    if search_query:
        movies = movies.filter(title__icontains=search_query)
    if selected_genre:
        movies = movies.filter(genre=selected_genre)

    movies = movies.only(
        'id',
        'title',
        'genre',
        'duration',
        'language',
        'poster',
    )
    page_obj = Paginator(movies, MOVIES_PER_PAGE).get_page(request.GET.get('page'))
    return render(
        request,
        'movies/movie_list.html',
        {
            'movies': page_obj.object_list,
            'page_obj': page_obj,
            'genres': genres,
            'search_query': search_query,
            'selected_genre': selected_genre,
            'has_filters': bool(search_query or selected_genre),
        },
    )


def movie_detail(request, pk):
    movie = get_object_or_404(
        Movie.objects.filter(is_active=True),
        pk=pk,
    )
    return render(request, 'movies/movie_detail.html', {'movie': movie})
