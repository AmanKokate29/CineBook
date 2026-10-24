from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from movies.models import Movie

from .models import Screen, Show, Theatre


class ShowtimeBrowsingTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title='Tomorrow at the Movies',
            description='An upcoming feature.',
            genre='Drama',
            duration=110,
            language='English',
            release_date=timezone.localdate(),
        )
        self.theatre = Theatre.objects.create(
            name='Grand Cinema',
            address='10 Main Street',
            city='Northport',
        )
        self.screen = Screen.objects.create(theatre=self.theatre, name='Screen One')

    def make_start(self, days=1, hour=18):
        local_date = timezone.localdate() + timedelta(days=days)
        return timezone.make_aware(
            datetime.combine(local_date, time(hour=hour)),
            timezone.get_current_timezone(),
        )

    def create_show(self, **overrides):
        start_time = overrides.pop('start_time', self.make_start())
        fields = {
            'movie': self.movie,
            'screen': self.screen,
            'start_time': start_time,
            'end_time': start_time + timedelta(minutes=110),
            'ticket_price': Decimal('14.50'),
            'is_active': True,
        }
        fields.update(overrides)
        return Show.objects.create(**fields)

    def test_showtimes_list_active_future_shows_grouped_by_theatre_and_screen(self):
        show = self.create_show()
        self.create_show(is_active=False, start_time=self.make_start(days=2))
        self.create_show(
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() - timedelta(days=1) + timedelta(minutes=110),
        )
        inactive_movie = Movie.objects.create(
            title='Inactive Feature',
            genre='Drama',
            duration=90,
            language='English',
            release_date=timezone.localdate(),
            is_active=False,
        )
        self.create_show(movie=inactive_movie, start_time=self.make_start(days=3))

        response = self.client.get(
            reverse('theatres:movie_showtimes', args=[self.movie.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.movie.title)
        self.assertContains(response, self.theatre.name)
        self.assertContains(response, self.theatre.address)
        self.assertContains(response, self.theatre.city)
        self.assertContains(response, self.screen.name)
        self.assertContains(response, '14.50')
        self.assertContains(response, reverse('theatres:select_seats', args=[show.pk]))
        self.assertContains(response, 'Select seats')
        self.assertNotContains(response, 'Inactive Feature')
        self.assertEqual(list(response.context['shows']), [show])

    def test_selected_date_filters_showtimes(self):
        selected_show = self.create_show(start_time=self.make_start(days=2))
        other_show = self.create_show(start_time=self.make_start(days=3))
        selected_date = selected_show.start_time.astimezone(
            timezone.get_current_timezone()
        ).date()

        response = self.client.get(
            reverse('theatres:movie_showtimes', args=[self.movie.pk]),
            {'date': selected_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_date'], selected_date)
        self.assertEqual(list(response.context['shows']), [selected_show])
        self.assertNotContains(response, reverse('theatres:select_seats', args=[other_show.pk]))

    def test_invalid_date_is_handled_without_server_error(self):
        show = self.create_show()

        response = self.client.get(
            reverse('theatres:movie_showtimes', args=[self.movie.pk]),
            {'date': 'not-a-date'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['date_error'])
        self.assertEqual(response.context['selected_date'], show.start_time.date())
        self.assertContains(response, 'That date was not valid')
        self.assertContains(response, 'Select seats')

    def test_valid_date_without_shows_displays_empty_date_state(self):
        self.create_show()
        unavailable_date = timezone.localdate() + timedelta(days=5)

        response = self.client.get(
            reverse('theatres:movie_showtimes', args=[self.movie.pk]),
            {'date': unavailable_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No showtimes on')
        self.assertEqual(list(response.context['shows']), [])

    def test_movie_without_available_shows_has_helpful_empty_state(self):
        response = self.client.get(
            reverse('theatres:movie_showtimes', args=[self.movie.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'There are no upcoming showtimes')

    def test_inactive_or_unknown_movie_showtimes_return_404(self):
        inactive_movie = Movie.objects.create(
            title='Inactive Movie',
            genre='Drama',
            duration=90,
            language='English',
            release_date=timezone.localdate(),
            is_active=False,
        )

        for movie_id in (inactive_movie.pk, inactive_movie.pk + 1):
            with self.subTest(movie_id=movie_id):
                response = self.client.get(
                    reverse('theatres:movie_showtimes', args=[movie_id])
                )
                self.assertEqual(response.status_code, 404)

    def test_seat_selection_route_checks_show_availability(self):
        available_show = self.create_show()
        inactive_show = self.create_show(
            is_active=False,
            start_time=self.make_start(days=2),
        )
        past_show = self.create_show(
            start_time=timezone.now() - timedelta(days=2),
            end_time=timezone.now() - timedelta(days=2) + timedelta(minutes=110),
        )

        response = self.client.get(
            reverse('theatres:select_seats', args=[available_show.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seat selection is coming soon')
        self.assertContains(response, available_show.movie.title)
        self.assertContains(response, available_show.screen.theatre.name)

        for show_id in (inactive_show.pk, past_show.pk, available_show.pk + 1000):
            with self.subTest(show_id=show_id):
                unavailable = self.client.get(
                    reverse('theatres:select_seats', args=[show_id])
                )
                self.assertEqual(unavailable.status_code, 404)

    def test_showtime_page_has_bounded_database_queries(self):
        self.create_show()

        with self.assertNumQueries(3):
            response = self.client.get(
                reverse('theatres:movie_showtimes', args=[self.movie.pk])
            )

        self.assertEqual(response.status_code, 200)
