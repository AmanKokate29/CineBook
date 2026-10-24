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
        self.assertEqual(len(response.context['movies']), 12)
