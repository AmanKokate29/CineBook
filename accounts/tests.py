from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AccountAuthenticationTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username='screenfan',
            password='SecureTestPass!825',
        )

    def test_registration_creates_hashed_password_and_signs_user_in(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'newcinegoer',
                'password1': 'SecureTestPass!825',
                'password2': 'SecureTestPass!825',
            },
        )

        self.assertRedirects(response, reverse('bookings:my_bookings'))
        new_user = self.user_model.objects.get(username='newcinegoer')
        self.assertTrue(new_user.check_password('SecureTestPass!825'))
        self.assertNotEqual(new_user.password, 'SecureTestPass!825')
        self.assertIn('_auth_user_id', self.client.session)
        self.assertContains(self.client.get(reverse('bookings:my_bookings')), 'No bookings yet')

    def test_registration_rejects_duplicate_username(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': self.user.username,
                'password1': 'AnotherSecurePass!825',
                'password2': 'AnotherSecurePass!825',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A user with that username already exists.')
        self.assertEqual(self.user_model.objects.filter(username=self.user.username).count(), 1)

    def test_login_redirects_to_requested_private_page(self):
        response = self.client.post(
            reverse('accounts:login'),
            {
                'username': self.user.username,
                'password': 'SecureTestPass!825',
                'next': reverse('bookings:my_bookings'),
            },
        )

        self.assertRedirects(response, reverse('bookings:my_bookings'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_invalid_login_shows_validation_error(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': self.user.username, 'password': 'incorrect'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct username and password.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_private_profile_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse('accounts:profile'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:profile')}",
        )

    def test_logout_requires_post_and_ends_session(self):
        self.client.force_login(self.user)

        get_response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(get_response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

        post_response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(post_response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse('accounts:register'),
            {
                'username': 'csrfcheck',
                'password1': 'SecureTestPass!825',
                'password2': 'SecureTestPass!825',
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.user_model.objects.filter(username='csrfcheck').exists())
