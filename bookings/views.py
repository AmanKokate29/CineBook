from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Booking


def _booking_queryset_for(user):
    return (
        Booking.objects.filter(user=user)
        .select_related('show__movie', 'show__screen__theatre')
        .prefetch_related('booked_seats__seat__screen')
    )


@login_required
def my_bookings(request):
    bookings = _booking_queryset_for(request.user)
    return render(request, 'bookings/my_bookings.html', {'bookings': bookings})


@login_required
@require_GET
def booking_detail(request, reference):
    booking = get_object_or_404(
        _booking_queryset_for(request.user),
        reference=reference,
    )
    return render(request, 'bookings/booking_detail.html', {'booking': booking})


@login_required
@require_GET
def confirmation(request, reference):
    booking = get_object_or_404(
        _booking_queryset_for(request.user),
        reference=reference,
    )
    return render(request, 'bookings/confirmation.html', {'booking': booking})
