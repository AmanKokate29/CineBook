from django.urls import path

from .views import (
    booking_calendar,
    booking_detail,
    cancel_booking,
    confirmation,
    my_bookings,
)

app_name = 'bookings'

urlpatterns = [
    path('', my_bookings, name='my_bookings'),
    path('<uuid:reference>/cancel/', cancel_booking, name='cancel'),
    path('<uuid:reference>/calendar/', booking_calendar, name='calendar'),
    path('<uuid:reference>/', booking_detail, name='detail'),
    path('<uuid:reference>/confirmation/', confirmation, name='confirmation'),
]
