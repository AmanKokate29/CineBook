from django.contrib.auth.decorators import login_required
from django.shortcuts import render

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
