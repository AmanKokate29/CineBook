from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from movies.models import Movie
from theatres.models import Screen, Seat, Show, Theatre

from .models import ActiveSeatClaim, BookedSeat, Booking


class ActiveSeatClaimTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='cinebook-test')
        self.theatre = Theatre.objects.create(
            name='Test Theatre',
            address='1 Test Street',
            city='Test City',
        )
        self.screen = Screen.objects.create(theatre=self.theatre, name='Screen 1')
        self.seat = Seat.objects.create(
            screen=self.screen,
            row_identifier='A',
            seat_number=1,
        )
        self.movie = Movie.objects.create(
            title='Test Movie',
            genre='Drama',
            duration=100,
            language='English',
            release_date=timezone.localdate(),
        )
        starts = timezone.now() + timedelta(days=1)
        self.show = Show.objects.create(
            movie=self.movie,
            screen=self.screen,
            start_time=starts,
            end_time=starts + timedelta(minutes=100),
            ticket_price=Decimal('12.50'),
        )
        self.booking, self.booked_seat = self.create_booking_and_seat(self.show)
        self.claim = ActiveSeatClaim.objects.create(
            booked_seat=self.booked_seat,
            show=self.show,
            seat=self.seat,
        )

    def create_booking_and_seat(self, show):
        booking = Booking.objects.create(
            user=self.user,
            show=show,
            total_amount=Decimal('12.50'),
        )
        booked_seat = BookedSeat.objects.create(
            booking=booking,
            show=show,
            seat=self.seat,
            price_paid=Decimal('12.50'),
        )
        return booking, booked_seat

    def test_database_prevents_duplicate_active_claim_for_show_and_seat(self):
        _, another_booked_seat = self.create_booking_and_seat(self.show)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ActiveSeatClaim.objects.create(
                    booked_seat=another_booked_seat,
                    show=self.show,
                    seat=self.seat,
                )

    def test_cancellation_releases_seat_and_preserves_history(self):
        self.booking.cancel()
        _, replacement_booked_seat = self.create_booking_and_seat(self.show)
        replacement_claim = ActiveSeatClaim.objects.create(
            booked_seat=replacement_booked_seat,
            show=self.show,
            seat=self.seat,
        )

        self.assertTrue(
            BookedSeat.objects.filter(
                pk=self.booked_seat.pk,
                status=BookedSeat.Status.RELEASED,
            ).exists()
        )
        self.assertEqual(
            Booking.objects.get(pk=self.booking.pk).status,
            Booking.Status.CANCELLED,
        )
        self.assertFalse(ActiveSeatClaim.objects.filter(pk=self.claim.pk).exists())
        self.assertEqual(replacement_claim.seat_id, self.seat.pk)

    def test_duplicate_seat_identifiers_are_rejected_per_screen(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Seat.objects.create(
                    screen=self.screen,
                    row_identifier=self.seat.row_identifier,
                    seat_number=self.seat.seat_number,
                )

    def test_same_seat_can_be_claimed_for_a_different_show(self):
        starts = timezone.now() + timedelta(days=2)
        another_show = Show.objects.create(
            movie=self.movie,
            screen=self.screen,
            start_time=starts,
            end_time=starts + timedelta(minutes=100),
            ticket_price=Decimal('12.50'),
        )
        _, booked_seat = self.create_booking_and_seat(another_show)

        claim = ActiveSeatClaim.objects.create(
            booked_seat=booked_seat,
            show=another_show,
            seat=self.seat,
        )

        self.assertEqual(claim.show_id, another_show.pk)


class BookingHistoryAccessTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='booking-owner',
            password='SecureTestPass!825',
        )
        self.other_user = user_model.objects.create_user(
            username='other-customer',
            password='SecureTestPass!825',
        )
        theatre = Theatre.objects.create(
            name='History Theatre',
            address='5 Cinema Road',
            city='Test City',
        )
        screen = Screen.objects.create(theatre=theatre, name='Screen A')
        movie = Movie.objects.create(
            title='History Test Film',
            genre='Drama',
            duration=110,
            language='English',
            release_date=timezone.localdate(),
        )
        starts = timezone.now() + timedelta(days=1)
        show = Show.objects.create(
            movie=movie,
            screen=screen,
            start_time=starts,
            end_time=starts + timedelta(minutes=110),
            ticket_price=Decimal('15.00'),
        )
        self.owner_booking = Booking.objects.create(
            user=self.owner,
            show=show,
            total_amount=Decimal('15.00'),
        )
        self.other_booking = Booking.objects.create(
            user=self.other_user,
            show=show,
            total_amount=Decimal('15.00'),
        )

    def test_booking_history_requires_login(self):
        response = self.client.get('/bookings/')

        self.assertRedirects(response, '/accounts/login/?next=/bookings/')

    def test_booking_history_only_displays_signed_in_users_bookings(self):
        self.client.force_login(self.owner)

        response = self.client.get('/bookings/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.owner_booking.reference))
        self.assertNotContains(response, str(self.other_booking.reference))
