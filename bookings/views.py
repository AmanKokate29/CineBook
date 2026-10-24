from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Booking


@login_required
def my_bookings(request):
    bookings = (
        Booking.objects.filter(user=request.user)
        .select_related('show__movie', 'show__screen__theatre')
        .prefetch_related(
            'booked_seats__seat__screen__theatre',
            'booked_seats__show__movie',
        )
    )
    return render(request, 'bookings/my_bookings.html', {'bookings': bookings})


@login_required
@require_GET
def confirmation(request, reference):
    booking = get_object_or_404(
        Booking.objects.filter(user=request.user)
        .select_related('show__movie', 'show__screen__theatre')
        .prefetch_related('booked_seats__seat__screen'),
        reference=reference,
    )
    return render(request, 'bookings/confirmation.html', {'booking': booking})
