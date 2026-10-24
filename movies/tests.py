from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Movie


class FrontendLayoutTests(TestCase):
    def test_homepage_renders_shared_layout_and_navigation(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CineBook')
        self.assertContains(response, 'Skip to content')
        self.assertContains(response, reverse('home'))
        self.assertContains(response, reverse('bookings:my_bookings'))
        self.assertContains(response, reverse('accounts:login'))
        self.assertContains(response, '/static/css/style.css')
        self.assertContains(response, '/static/js/main.js')

    def test_navigation_destinations_render_placeholders(self):
        for route_name in ('movies:list',):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Back to home')

    def test_login_link_opens_login_form(self):
        response = self.client.get(reverse('accounts:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in to CineBook')

    def test_booking_link_redirects_anonymous_visitors_to_login(self):
        response = self.client.get(reverse('bookings:my_bookings'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('bookings:my_bookings')}",
        )

    def test_static_assets_are_discoverable(self):
        self.assertIsNotNone(finders.find('css/style.css'))
        self.assertIsNotNone(finders.find('js/main.js'))


class MovieBrowsingTests(TestCase):
    def create_movie(self, **overrides):
        fields = {
            'title': 'A CineBook Story',
            'description': 'A journey across the stars.',
            'genre': 'Science Fiction',
            'duration': 124,
            'language': 'English',
            'release_date': timezone.localdate(),
            'is_active': True,
        }
        fields.update(overrides)
        return Movie.objects.create(**fields)

    def test_movie_list_shows_active_movies_and_excludes_inactive_movies(self):
        active_movie = self.create_movie()
        self.create_movie(title='Hidden Film', is_active=False)

        response = self.client.get(reverse('movies:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, active_movie.title)
        self.assertContains(response, active_movie.genre)
        self.assertContains(response, '124 min')
        self.assertContains(response, active_movie.language)
        self.assertContains(response, 'No poster available')
        self.assertNotContains(response, 'Hidden Film')
        self.assertEqual(len(response.context['movies']), 1)

    def test_movie_list_shows_empty_state_when_no_active_movies_exist(self):
        self.create_movie(is_active=False)

        response = self.client.get(reverse('movies:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No movies available right now')
        self.assertNotContains(response, 'A CineBook Story')

    def test_movie_detail_shows_description_metadata_and_booking_placeholder(self):
        movie = self.create_movie()

        response = self.client.get(reverse('movies:detail', args=[movie.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, movie.title)
        self.assertContains(response, movie.description)
        self.assertContains(response, movie.genre)
        self.assertContains(response, movie.language)
        self.assertContains(response, 'Book tickets')
        self.assertContains(response, 'booking is coming soon')
        self.assertContains(response, 'No poster available')

    def test_inactive_or_unknown_movie_detail_returns_404(self):
        inactive_movie = self.create_movie(is_active=False)

        for movie_id in (inactive_movie.pk, inactive_movie.pk + 1):
            with self.subTest(movie_id=movie_id):
                response = self.client.get(reverse('movies:detail', args=[movie_id]))
                self.assertEqual(response.status_code, 404)

    def test_list_page_uses_one_movie_query(self):
        self.create_movie()

        with self.assertNumQueries(1):
            response = self.client.get(reverse('movies:list'))

        self.assertEqual(response.status_code, 200)
