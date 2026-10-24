from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from movies.models import Movie

from .models import Show


def movie_showtimes(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id, is_active=True)
    now = timezone.now()
    available_shows = Show.objects.filter(
        movie=movie,
        movie__is_active=True,
        is_active=True,
        start_time__gte=now,
    ).select_related('screen__theatre', 'movie')
    available_dates = list(available_shows.dates('start_time', 'day'))

    requested_date = request.GET.get('date', '').strip()
    parsed_date = parse_date(requested_date) if requested_date else None
    date_error = bool(requested_date and parsed_date is None)

    if parsed_date:
        selected_date = parsed_date
    elif available_dates:
        selected_date = available_dates[0]
    else:
        selected_date = timezone.localdate()

    current_timezone = timezone.get_current_timezone()
    date_start = timezone.make_aware(
        datetime.combine(selected_date, time.min),
        current_timezone,
    )
    next_date_start = timezone.make_aware(
        datetime.combine(selected_date + timedelta(days=1), time.min),
        current_timezone,
    )
    shows = available_shows.filter(
        start_time__gte=max(date_start, now),
        start_time__lt=next_date_start,
    ).order_by('screen__theatre__city', 'screen__theatre__name', 'screen__name', 'start_time')

    return render(
        request,
        'theatres/movie_showtimes.html',
        {
            'movie': movie,
            'available_dates': available_dates,
            'selected_date': selected_date,
            'shows': shows,
            'date_error': date_error,
        },
    )


def select_seats(request, show_id):
    show = get_object_or_404(
        Show.objects.select_related('movie', 'screen__theatre'),
        pk=show_id,
        is_active=True,
        movie__is_active=True,
        start_time__gte=timezone.now(),
    )
    return render(request, 'theatres/seat_selection_unavailable.html', {'show': show})
