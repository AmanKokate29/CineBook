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
        for route_name in ('movies:list', 'bookings:my_bookings', 'accounts:login'):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Back to home')

    def test_static_assets_are_discoverable(self):
        self.assertIsNotNone(finders.find('css/style.css'))
        self.assertIsNotNone(finders.find('js/main.js'))
