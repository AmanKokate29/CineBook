from django.urls import path

from .views import confirmation, my_bookings

app_name = 'bookings'

urlpatterns = [
    path('', my_bookings, name='my_bookings'),
    path('<uuid:reference>/confirmation/', confirmation, name='confirmation'),
]
