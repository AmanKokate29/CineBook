from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Booking, BookingCancellationError


def _booking_queryset_for(user):
    return (
        Booking.objects.filter(user=user)
        .select_related('show__movie', 'show__screen__theatre')
        .prefetch_related('booked_seats__seat__screen')
    )


@login_required
def my_bookings(request):
    now = timezone.now()
    bookings = list(_booking_queryset_for(request.user))
    for booking in bookings:
        booking.can_cancel = (
            booking.status in (Booking.Status.PENDING, Booking.Status.CONFIRMED)
            and booking.show.start_time > now
        )
    return render(
        request,
        'bookings/my_bookings.html',
        {'bookings': bookings},
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
