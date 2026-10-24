from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import (
    IntegrityError,
    close_old_connections,
    connections,
    transaction,
)
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from movies.models import Movie
from theatres.models import Screen, Seat, Show, Theatre

from .models import ActiveSeatClaim, BookedSeat, Booking
from .services import BookingConflict, BookingRequestError, create_booking


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
            status=Booking.Status.CONFIRMED,
        )
        self.other_booking = Booking.objects.create(
            user=self.other_user,
            show=show,
            total_amount=Decimal('15.00'),
        )
        seat = Seat.objects.create(
            screen=screen,
            row_identifier='B',
            seat_number=4,
        )
        self.owner_booked_seat = BookedSeat.objects.create(
            booking=self.owner_booking,
            show=show,
            seat=seat,
            price_paid=Decimal('15.00'),
        )
        self.owner_claim = ActiveSeatClaim.objects.create(
            booked_seat=self.owner_booked_seat,
            show=show,
            seat=seat,
        )

    def test_booking_history_requires_login(self):
        response = self.client.get('/bookings/')

        self.assertRedirects(response, '/accounts/login/?next=/bookings/')

    def test_booking_history_only_displays_signed_in_users_bookings(self):
        self.client.force_login(self.owner)

        response = self.client.get('/bookings/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.owner_booking.reference))
        self.assertContains(response, 'History Test Film')
        self.assertContains(response, 'History Theatre')
        self.assertContains(response, 'Screen A')
        self.assertContains(response, 'B4')
        self.assertContains(response, '15.00')
        self.assertContains(
            response,
            reverse('bookings:detail', args=[self.owner_booking.reference]),
        )
        self.assertNotContains(response, str(self.other_booking.reference))

    def test_booking_history_displays_empty_state(self):
        user_with_no_bookings = get_user_model().objects.create_user(
            username='no-bookings-customer',
        )
        self.client.force_login(user_with_no_bookings)

        response = self.client.get(reverse('bookings:my_bookings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No bookings yet')
        self.assertContains(response, reverse('movies:list'))

    def test_booking_detail_requires_login_and_only_owner_can_view(self):
        url = reverse('bookings:detail', args=[self.owner_booking.reference])

        response = self.client.get(url)
        self.assertRedirects(response, f'/accounts/login/?next={url}')

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'History Test Film')
        self.assertContains(response, 'History Theatre')
        self.assertContains(response, 'Screen A')
        self.assertContains(response, 'B4')
        self.assertContains(response, 'Confirmed')
        self.assertContains(response, '15.00')

    def test_confirmation_requires_login_and_only_owner_can_view(self):
        url = reverse('bookings:confirmation', args=[self.owner_booking.reference])

        response = self.client.get(url)
        self.assertRedirects(response, f'/accounts/login/?next={url}')

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No payment was processed')

    def test_owner_can_cancel_with_post_and_seats_are_released(self):
        self.client.force_login(self.owner)
        url = reverse('bookings:cancel', args=[self.owner_booking.reference])

        response = self.client.post(url, follow=True)

        self.assertRedirects(
            response,
            reverse('bookings:detail', args=[self.owner_booking.reference]),
        )
        self.assertEqual(
            Booking.objects.get(pk=self.owner_booking.pk).status,
            Booking.Status.CANCELLED,
        )
        self.assertEqual(
            BookedSeat.objects.get(pk=self.owner_booked_seat.pk).status,
            BookedSeat.Status.RELEASED,
        )
        self.assertFalse(
            ActiveSeatClaim.objects.filter(pk=self.owner_claim.pk).exists()
        )
        self.assertContains(response, 'has been cancelled', status_code=200)
        self.assertContains(response, 'retained')

    def test_cancellation_rejects_get_repeats_and_other_users(self):
        url = reverse('bookings:cancel', args=[self.owner_booking.reference])
        self.client.force_login(self.owner)

        self.assertEqual(self.client.get(url).status_code, 405)

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(
            Booking.objects.get(pk=self.owner_booking.pk).status,
            Booking.Status.CONFIRMED,
        )

        self.client.force_login(self.owner)
        self.client.post(url)
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already been cancelled')
        self.assertEqual(
            BookedSeat.objects.get(pk=self.owner_booked_seat.pk).status,
            BookedSeat.Status.RELEASED,
        )

    def test_started_show_cannot_be_cancelled(self):
        self.owner_booking.show.start_time = timezone.now() - timedelta(minutes=1)
        self.owner_booking.show.save(update_fields=['start_time'])
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('bookings:cancel', args=[self.owner_booking.reference]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'only be cancelled before the show starts')
        self.assertEqual(
            Booking.objects.get(pk=self.owner_booking.pk).status,
            Booking.Status.CONFIRMED,
        )
        self.assertEqual(
            BookedSeat.objects.get(pk=self.owner_booked_seat.pk).status,
            BookedSeat.Status.ACTIVE,
        )
        self.assertTrue(
            ActiveSeatClaim.objects.filter(pk=self.owner_claim.pk).exists()
        )

    def test_cancellation_post_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        url = reverse('bookings:cancel', args=[self.owner_booking.reference])
        csrf_client.get(reverse('bookings:detail', args=[self.owner_booking.reference]))

        response = csrf_client.post(url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            Booking.objects.get(pk=self.owner_booking.pk).status,
            Booking.Status.CONFIRMED,
        )


class BookingServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='service-customer')
        self.theatre = Theatre.objects.create(
            name='Service Cinema',
            address='2 Booking Road',
            city='Northport',
        )
        self.screen = Screen.objects.create(theatre=self.theatre, name='Screen 1')
        self.seats = [
            Seat.objects.create(screen=self.screen, row_identifier='A', seat_number=n)
            for n in (1, 2)
        ]
        self.movie = Movie.objects.create(
            title='Service Test Film',
            genre='Drama',
            duration=100,
            language='English',
            release_date=timezone.localdate(),
        )
        start = timezone.now() + timedelta(days=1)
        self.show = Show.objects.create(
            movie=self.movie,
            screen=self.screen,
            start_time=start,
            end_time=start + timedelta(minutes=100),
            ticket_price=Decimal('13.75'),
        )

    def test_service_rejects_duplicate_and_invalid_selections(self):
        for seat_ids in ([str(self.seats[0].pk)] * 2, ['invalid']):
            with self.subTest(seat_ids=seat_ids):
                with self.assertRaises(BookingRequestError):
                    create_booking(
                        user=self.user,
                        show_id=self.show.pk,
                        submitted_seat_ids=seat_ids,
                    )
        self.assertFalse(Booking.objects.exists())

    def test_booking_references_are_unique_in_the_database(self):
        first = create_booking(
            user=self.user,
            show_id=self.show.pk,
            submitted_seat_ids=[str(self.seats[0].pk)],
        )
        second = create_booking(
            user=self.user,
            show_id=self.show.pk,
            submitted_seat_ids=[str(self.seats[1].pk)],
        )

        self.assertNotEqual(first.reference, second.reference)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Booking.objects.create(
                    user=self.user,
                    show=self.show,
                    reference=first.reference,
                    total_amount=Decimal('13.75'),
                )

        self.assertEqual(Booking.objects.filter(show=self.show).count(), 2)

    def test_service_rejects_inactive_and_started_shows(self):
        self.show.is_active = False
        self.show.save(update_fields=['is_active'])
        with self.assertRaises(BookingRequestError):
            create_booking(
                user=self.user,
                show_id=self.show.pk,
                submitted_seat_ids=[str(self.seats[0].pk)],
            )

        self.show.is_active = True
        self.show.start_time = timezone.now() - timedelta(minutes=1)
        self.show.save(update_fields=['is_active', 'start_time'])
        with self.assertRaises(BookingRequestError):
            create_booking(
                user=self.user,
                show_id=self.show.pk,
                submitted_seat_ids=[str(self.seats[0].pk)],
            )
        self.assertFalse(Booking.objects.exists())

    def test_mid_transaction_claim_conflict_rolls_back_entire_booking(self):
        real_create = ActiveSeatClaim.objects.create
        calls = 0

        def create_then_conflict(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                cause = Exception(
                    1062,
                    "Duplicate entry for key 'unique_active_claim_per_show_seat'",
                )
                raise IntegrityError(*cause.args) from cause
            return real_create(**kwargs)

        with patch.object(ActiveSeatClaim.objects, 'create', side_effect=create_then_conflict):
            with self.assertRaises(BookingConflict):
                create_booking(
                    user=self.user,
                    show_id=self.show.pk,
                    submitted_seat_ids=[str(seat.pk) for seat in self.seats],
                )

        self.assertFalse(Booking.objects.exists())
        self.assertFalse(BookedSeat.objects.exists())
        self.assertFalse(ActiveSeatClaim.objects.exists())

    def test_cancelled_booking_keeps_history_and_allows_rebooking(self):
        first = create_booking(
            user=self.user,
            show_id=self.show.pk,
            submitted_seat_ids=[str(self.seats[0].pk)],
        )
        history_row = first.booked_seats.get()
        first.cancel()

        replacement = create_booking(
            user=self.user,
            show_id=self.show.pk,
            submitted_seat_ids=[str(self.seats[0].pk)],
        )

        history_row.refresh_from_db()
        self.assertEqual(history_row.status, BookedSeat.Status.RELEASED)
        self.assertEqual(
            Booking.objects.get(pk=first.pk).status,
            Booking.Status.CANCELLED,
        )
        self.assertEqual(replacement.booked_seats.count(), 1)
        self.assertEqual(ActiveSeatClaim.objects.filter(show=self.show).count(), 1)


@skipUnlessDBFeature('has_select_for_update')
class ConcurrentBookingTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user_model = get_user_model()
        self.user_one = self.user_model.objects.create_user(username='concurrent-one')
        self.user_two = self.user_model.objects.create_user(username='concurrent-two')
        theatre = Theatre.objects.create(
            name='Concurrency Cinema',
            address='3 Race Condition Avenue',
            city='Northport',
        )
        screen = Screen.objects.create(theatre=theatre, name='Screen 1')
        self.seat = Seat.objects.create(screen=screen, row_identifier='A', seat_number=1)
        movie = Movie.objects.create(
            title='Concurrency Film',
            genre='Drama',
            duration=100,
            language='English',
            release_date=timezone.localdate(),
        )
        start = timezone.now() + timedelta(days=1)
        self.show = Show.objects.create(
            movie=movie,
            screen=screen,
            start_time=start,
            end_time=start + timedelta(minutes=100),
            ticket_price=Decimal('10.00'),
        )

    def test_only_one_concurrent_request_can_claim_a_seat(self):
        barrier = Barrier(2)

        def attempt(user_id):
            close_old_connections()
            try:
                user = self.user_model.objects.get(pk=user_id)
                barrier.wait(timeout=10)
                return create_booking(
                    user=user,
                    show_id=self.show.pk,
                    submitted_seat_ids=[str(self.seat.pk)],
                )
            except BookingConflict:
                return None
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(attempt, self.user_one.pk),
                executor.submit(attempt, self.user_two.pk),
            ]
            results = [future.result(timeout=30) for future in futures]

        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(Booking.objects.filter(show=self.show).count(), 1)
        self.assertEqual(ActiveSeatClaim.objects.filter(show=self.show).count(), 1)
