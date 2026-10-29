from datetime import timezone as datetime_timezone

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Booking, BookingCancellationError


BOOKINGS_PER_PAGE = 10


def _escape_ical_text(value):
    return (
        str(value)
        .replace('\\', '\\\\')
        .replace('\r\n', '\n')
        .replace('\r', '\n')
        .replace('\n', '\\n')
        .replace(',', '\\,')
        .replace(';', '\\;')
    )


def _fold_ical_line(line):
    chunks = []
    current_chunk = ''
    byte_limit = 75
    for character in line:
        if len((current_chunk + character).encode('utf-8')) > byte_limit:
            chunks.append(current_chunk)
            current_chunk = character
            byte_limit = 74
        else:
            current_chunk += character
    chunks.append(current_chunk)
    return '\r\n '.join(chunks)


def _booking_queryset_for(user):
    return (
        Booking.objects.filter(user=user).order_by('-created_at', '-pk')
        .select_related('show__movie', 'show__screen__theatre')
        .prefetch_related('booked_seats__seat')
    )


@login_required
def my_bookings(request):
    now = timezone.now()
    page_obj = Paginator(
        _booking_queryset_for(request.user),
        BOOKINGS_PER_PAGE,
    ).get_page(request.GET.get('page'))
    bookings = list(page_obj.object_list)
    for booking in bookings:
        booking.can_cancel = (
            booking.status in (Booking.Status.PENDING, Booking.Status.CONFIRMED)
            and booking.show.start_time > now
        )
    return render(
        request,
        'bookings/my_bookings.html',
        {'bookings': bookings, 'page_obj': page_obj},
    )


@login_required
@require_GET
def booking_detail(request, reference):
    booking = get_object_or_404(
        _booking_queryset_for(request.user),
        reference=reference,
    )
    booking.can_cancel = (
        booking.status in (Booking.Status.PENDING, Booking.Status.CONFIRMED)
        and booking.show.start_time > timezone.now()
    )
    return render(
        request,
        'bookings/booking_detail.html',
        {'booking': booking},
    )


@login_required
@require_POST
def cancel_booking(request, reference):
    booking = get_object_or_404(
        Booking.objects.filter(user=request.user),
        reference=reference,
    )
    try:
        booking.cancel()
    except BookingCancellationError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(
            request,
            f'Booking {booking.reference} has been cancelled. '
            'Its seats are available to book again.',
        )
    return redirect('bookings:detail', reference=booking.reference)


@login_required
@require_GET
def confirmation(request, reference):
    booking = get_object_or_404(
        _booking_queryset_for(request.user),
        reference=reference,
    )
    return render(request, 'bookings/confirmation.html', {'booking': booking})


@login_required
@require_GET
def booking_calendar(request, reference):
    booking = get_object_or_404(
        _booking_queryset_for(request.user),
        reference=reference,
    )
    show = booking.show
    theatre = show.screen.theatre
    starts_at = show.start_time.astimezone(datetime_timezone.utc)
    ends_at = show.end_time.astimezone(datetime_timezone.utc)
    location = ', '.join(
        value
        for value in (
            theatre.name,
            show.screen.name,
            theatre.address,
            theatre.city,
        )
        if value
    )
    seats = ', '.join(
        f'{booked_seat.seat.row_identifier}{booked_seat.seat.seat_number}'
        for booked_seat in booking.booked_seats.all()
    )
    description = f'Booking reference: {booking.reference}'
    if seats:
        description += f'\nSeats: {seats}'

    calendar_lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//CineBook//Booking Calendar//EN',
        'CALSCALE:GREGORIAN',
        'BEGIN:VEVENT',
        f'UID:{booking.reference}@cinebook',
        f'DTSTAMP:{timezone.now().astimezone(datetime_timezone.utc):%Y%m%dT%H%M%SZ}',
        f'DTSTART:{starts_at:%Y%m%dT%H%M%SZ}',
        f'DTEND:{ends_at:%Y%m%dT%H%M%SZ}',
        f'SUMMARY:{_escape_ical_text(show.movie.title)}',
        f'LOCATION:{_escape_ical_text(location)}',
        f'DESCRIPTION:{_escape_ical_text(description)}',
        'END:VEVENT',
        'END:VCALENDAR',
    ]
    response = HttpResponse(
        '\r\n'.join(_fold_ical_line(line) for line in calendar_lines) + '\r\n',
        content_type='text/calendar; charset=utf-8',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="cinebook-{booking.reference}.ics"'
    )
    return response
