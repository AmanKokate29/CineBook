from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


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
