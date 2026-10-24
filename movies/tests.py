import json
import os
import tempfile
from io import BytesIO, StringIO
from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

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
        for genre in (
            'adventure',
            'drama',
            'family',
            'mystery',
            'romance',
            'science-fiction',
            'default',
        ):
            with self.subTest(genre=genre):
                self.assertIsNotNone(
                    finders.find(f'images/posters/{genre}.svg')
                )


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
        self.assertContains(response, 'Illustrated poster artwork')
        self.assertContains(response, '/static/images/posters/science-fiction.svg')
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
        self.assertContains(response, 'View showtimes')
        self.assertContains(response, reverse('theatres:movie_showtimes', args=[movie.pk]))
        self.assertContains(response, 'No poster available')

    def test_inactive_or_unknown_movie_detail_returns_404(self):
        inactive_movie = self.create_movie(is_active=False)

        for movie_id in (inactive_movie.pk, inactive_movie.pk + 1):
            with self.subTest(movie_id=movie_id):
                response = self.client.get(reverse('movies:detail', args=[movie_id]))
                self.assertEqual(response.status_code, 404)

    def test_list_page_uses_bounded_database_queries(self):
        self.create_movie()

        with self.assertNumQueries(3):
            response = self.client.get(reverse('movies:list'))

        self.assertEqual(response.status_code, 200)

    def test_search_filters_by_title_case_insensitively(self):
        match = self.create_movie(title='Silver Comet')
        self.create_movie(title='Quiet Harbor')

        response = self.client.get(reverse('movies:list'), {'q': '  sIlVeR  '})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, match.title)
        self.assertNotContains(response, 'Quiet Harbor')
        self.assertEqual(response.context['search_query'], 'sIlVeR')
        self.assertContains(response, 'value="sIlVeR"', html=False)

    def test_genre_filter_preserves_selection_and_ignores_inactive_genres(self):
        action_movie = self.create_movie(title='Action Film', genre='Action')
        self.create_movie(title='Comedy Film', genre='Comedy')
        self.create_movie(title='Inactive Horror', genre='Horror', is_active=False)

        response = self.client.get(reverse('movies:list'), {'genre': 'action'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, action_movie.title)
        self.assertNotContains(response, 'Comedy Film')
        self.assertNotContains(response, 'Inactive Horror')
        self.assertEqual(response.context['selected_genre'], 'Action')
        self.assertContains(response, '<option value="Action" selected>', html=False)
        self.assertNotContains(response, '<option value="Horror">', html=False)

    def test_search_and_genre_filters_combine(self):
        match = self.create_movie(title='Moonlit Mystery', genre='Mystery')
        self.create_movie(title='Moonlit Journey', genre='Adventure')
        self.create_movie(title='Daylight Mystery', genre='Mystery')

        response = self.client.get(
            reverse('movies:list'),
            {'q': 'Moonlit', 'genre': 'Mystery'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, match.title)
        self.assertNotContains(response, 'Moonlit Journey')
        self.assertNotContains(response, 'Daylight Mystery')

    def test_no_matches_shows_filter_empty_state(self):
        self.create_movie()

        response = self.client.get(
            reverse('movies:list'),
            {'q': 'No such title', 'genre': 'Science Fiction'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No movies match your filters')
        self.assertContains(response, 'Clear filters')

    def test_invalid_query_values_do_not_break_listing(self):
        long_search = 'x' * 500

        response = self.client.get(
            reverse('movies:list'),
            {'q': long_search, 'genre': 'Not a real genre', 'page': 'not-a-number'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['search_query']), 100)
        self.assertEqual(response.context['selected_genre'], '')
        self.assertContains(response, 'No movies match your filters')

    def test_pagination_preserves_search_and_genre_filters(self):
        for number in range(13):
            self.create_movie(title=f'Mystery Feature {number:02d}', genre='Mystery')

        response = self.client.get(
            reverse('movies:list'),
            {'q': 'Mystery', 'genre': 'Mystery', 'page': '1'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['movies']), 12)
        self.assertContains(response, '?q=Mystery&amp;genre=Mystery&amp;page=2')

    def test_invalid_page_number_falls_back_to_first_page(self):
        for number in range(13):
            self.create_movie(title=f'Feature {number:02d}')

        response = self.client.get(reverse('movies:list'), {'page': 'not-a-number'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 1)


class PosterSyncCommandTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title='A CineBook Story',
            description='A journey across the stars.',
            genre='Drama',
            duration=124,
            language='English',
            release_date=timezone.localdate().replace(year=2024),
            is_active=True,
        )
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)
        self.addCleanup(self.media_directory.cleanup)

    @staticmethod
    def _poster_bytes():
        image_data = BytesIO()
        Image.new('RGB', (20, 30), color=(180, 45, 60)).save(
            image_data,
            format='JPEG',
        )
        return image_data.getvalue()

    @staticmethod
    def _response(content, content_type='application/json'):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size=-1):
                return content if size < 0 else content[:size]

        response = FakeResponse()
        response.headers = {'Content-Type': content_type}
        return response

    def test_imports_exact_title_and_year_poster(self):
        search_response = self._response(
            json.dumps(
                {
                    'results': [
                        {
                            'title': self.movie.title,
                            'original_title': self.movie.title,
                            'release_date': f'{self.movie.release_date.year + 1}-06-01',
                            'poster_path': '/sample-poster.jpg',
                        }
                    ]
                }
            ).encode()
        )
        image_response = self._response(
            self._poster_bytes(),
            content_type='image/jpeg',
        )

        with (
            patch.dict(os.environ, {'TMDB_API_READ_ACCESS_TOKEN': 'test-token'}),
            patch(
                'movies.management.commands.sync_movie_posters.urlopen',
                side_effect=[search_response, image_response],
            ) as mock_urlopen,
        ):
            call_command('sync_movie_posters', stdout=StringIO())

        self.movie.refresh_from_db()
        self.assertTrue(self.movie.poster.name.endswith('-tmdb.jpg'))
        with self.movie.poster.open('rb') as poster:
            self.assertEqual(poster.read(), self._poster_bytes())
        self.assertEqual(mock_urlopen.call_count, 2)
        search_request = mock_urlopen.call_args_list[0].args[0]
        self.assertEqual(
            search_request.get_header('Authorization'),
            'Bearer test-token',
        )
        self.assertNotIn('year=', search_request.full_url)

    def test_rejects_non_exact_title_without_downloading(self):
        search_response = self._response(
            json.dumps(
                {
                    'results': [
                        {
                            'title': 'A Different Story',
                            'original_title': 'A Different Story',
                            'release_date': f'{self.movie.release_date.year}-06-01',
                            'poster_path': '/wrong-poster.jpg',
                        }
                    ]
                }
            ).encode()
        )

        with (
            patch.dict(os.environ, {'TMDB_API_READ_ACCESS_TOKEN': 'test-token'}),
            patch(
                'movies.management.commands.sync_movie_posters.urlopen',
                return_value=search_response,
            ) as mock_urlopen,
        ):
            call_command('sync_movie_posters', stdout=StringIO())

        self.movie.refresh_from_db()
        self.assertFalse(self.movie.poster)
        mock_urlopen.assert_called_once()

    def test_dry_run_does_not_download_or_save_poster(self):
        search_response = self._response(
            json.dumps(
                {
                    'results': [
                        {
                            'title': self.movie.title,
                            'original_title': self.movie.title,
                            'release_date': f'{self.movie.release_date.year}-06-01',
                            'poster_path': '/sample-poster.jpg',
                        }
                    ]
                }
            ).encode()
        )

        with (
            patch.dict(os.environ, {'TMDB_API_READ_ACCESS_TOKEN': 'test-token'}),
            patch(
                'movies.management.commands.sync_movie_posters.urlopen',
                return_value=search_response,
            ) as mock_urlopen,
        ):
            call_command('sync_movie_posters', '--dry-run', stdout=StringIO())

        self.movie.refresh_from_db()
        self.assertFalse(self.movie.poster)
        mock_urlopen.assert_called_once()

    def test_requires_api_token(self):
        with patch.dict(os.environ, {'TMDB_API_READ_ACCESS_TOKEN': ''}):
            with self.assertRaisesMessage(
                CommandError,
                'Set TMDB_API_READ_ACCESS_TOKEN',
            ):
                call_command('sync_movie_posters', stdout=StringIO())
