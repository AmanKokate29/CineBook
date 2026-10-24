from datetime import date, datetime, time, timedelta
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from bookings.models import ActiveSeatClaim, BookedSeat, Booking
from bookings.services import BookingConflict, BookingRequestError, create_booking
from movies.models import Movie

from .models import Seat, Show


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
    date_error = bool(
        requested_date
        and (parsed_date is None or parsed_date == date.max)
    )

    if parsed_date and not date_error:
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


@require_http_methods(['GET', 'POST'])
def select_seats(request, show_id):
    show = get_object_or_404(
        Show.objects.select_related('movie', 'screen__theatre'),
        pk=show_id,
        is_active=True,
        movie__is_active=True,
        start_time__gte=timezone.now(),
    )
    if request.method == 'POST' and not request.user.is_authenticated:
        messages.info(
            request,
            'Sign in to continue. Seat selections are not held, so please select them again after signing in.',
        )
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)

    seats = list(
        Seat.objects.filter(screen_id=show.screen_id).order_by(
            'row_identifier',
            'seat_number',
        )
    )
    unavailable_seat_ids = set(
        ActiveSeatClaim.objects.filter(
            show_id=show.pk,
            seat__screen_id=show.screen_id,
            booked_seat__show_id=show.pk,
            booked_seat__seat_id=F('seat_id'),
            booked_seat__status=BookedSeat.Status.ACTIVE,
            booked_seat__booking__show_id=show.pk,
            booked_seat__booking__status__in=(
                Booking.Status.PENDING,
                Booking.Status.CONFIRMED,
            ),
        ).values_list('seat_id', flat=True)
    )

    for seat in seats:
        seat.is_unavailable = seat.pk in unavailable_seat_ids

    errors = []
    selected_ids = []
    selected_seats = []
    estimated_total = show.ticket_price * 0
    response_status = 200
    if request.method == 'POST':
        submitted_ids = request.POST.getlist('seat_ids')
        try:
            booking = create_booking(
                user=request.user,
                show_id=show.pk,
                submitted_seat_ids=submitted_ids,
            )
        except BookingConflict as exc:
            errors.append(str(exc))
            response_status = 409
        except BookingRequestError as exc:
            errors.append(str(exc))
            response_status = 400
        else:
            messages.success(
                request,
                f'Booking confirmed. Reference: {booking.reference}. '
                'No payment was processed.',
            )
            return redirect('bookings:confirmation', reference=booking.reference)

        selected_ids = [
            int(seat_id)
            for seat_id in submitted_ids
            if re.fullmatch(r'[1-9][0-9]*', seat_id)
        ]
        selected_seats = [seat for seat in seats if seat.pk in selected_ids]
        estimated_total = show.ticket_price * len(selected_seats)

    return render(
        request,
        'theatres/seat_selection.html',
        {
            'show': show,
            'seats': seats,
            'unavailable_seat_ids': unavailable_seat_ids,
            'selected_seat_ids': selected_ids,
            'selected_seats': selected_seats,
            'estimated_total': estimated_total,
            'errors': errors,
        },
        status=response_status,
    )
