from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from users.services import GoogleOAuthService

OAUTH_SETTINGS = dict(
    GOOGLE_OAUTH_CLIENT_ID='id',
    GOOGLE_OAUTH_CLIENT_SECRET='secret',
    GOOGLE_OAUTH_REDIRECT_URI='http://testserver/users/google/callback/',
)


@override_settings(**OAUTH_SETTINGS)
class GoogleOAuthCallbackTest(TestCase):
    url = reverse('users:google_callback')

    def _callback(self, state):
        return self.client.get(self.url, {'code': 'c', 'state': state})

    @patch('users.views.GoogleOAuthService')
    def test_rejects_callback_without_session_state(self, service):
        response = self._callback('anything')
        self.assertRedirects(response, '/app/login?error=google', fetch_redirect_response=False)
        service.assert_not_called()

    @patch('users.views.GoogleOAuthService')
    def test_rejects_mismatched_state(self, service):
        session = self.client.session
        session['google_oauth_state'] = 'expected'
        session.save()
        self._callback('attacker')
        service.assert_not_called()

    @patch('users.views.GoogleOAuthService')
    def test_matching_state_logs_in_and_ignores_next(self, service):
        from users.models import User
        service.return_value.authenticate_or_create_user.return_value = User.objects.create_user('g', 'g@x.com')
        session = self.client.session
        session['google_oauth_state'] = 'ok'
        session.save()

        response = self.client.get(self.url, {'code': 'c', 'state': 'ok', 'next': 'https://evil.example'})

        self.assertRedirects(response, reverse('app'), fetch_redirect_response=False)
        self.assertNotIn('google_oauth_state', self.client.session)


@override_settings(**OAUTH_SETTINGS)
class GoogleEmailVerificationTest(TestCase):
    def test_unverified_email_is_rejected(self):
        with self.assertRaisesMessage(ValueError, 'not verified'):
            GoogleOAuthService().authenticate_or_create_user({'email': 'a@x.com', 'sub': '1', 'given_name': 'A'})

    def test_signs_in_by_google_id_not_email(self):
        from users.models import User
        google_user = GoogleOAuthService().authenticate_or_create_user(
            {'email': 'a@x.com', 'sub': '1', 'email_verified': True, 'given_name': 'A'})
        google_user.email = 'changed@x.com'  # they changed their email in Settings
        google_user.save()
        again = GoogleOAuthService().authenticate_or_create_user({'email': 'a@x.com', 'sub': '1', 'email_verified': True})
        self.assertEqual(again, google_user)
        self.assertEqual(User.objects.count(), 1)

    def test_never_links_to_an_account_that_claims_the_same_email(self):
        from users.models import User
        User.objects.create_user('attacker', 'Victim@gmail.com', 'pw')  # emails are not verified
        with self.assertRaisesMessage(ValueError, 'belongs to an account'):
            GoogleOAuthService().authenticate_or_create_user(
                {'email': 'victim@gmail.com', 'sub': '9', 'email_verified': True, 'given_name': 'V'})
        self.assertFalse(User.objects.filter(google_id='9').exists())

    def test_verified_email_creates_user(self):
        user = GoogleOAuthService().authenticate_or_create_user(
            {'email': 'a@x.com', 'sub': '1', 'email_verified': True, 'given_name': 'A'}
        )
        self.assertEqual(user.email, 'a@x.com')


class CareerPagesRedirectTest(TestCase):
    """The career pages and the old logout page were removed; their old URLs land in the app."""

    def test_old_career_urls_redirect_to_the_app(self):
        for url in ['/learning/dashboard/', '/learning/dream-path/', '/learning/course/1/detail/',
                    '/users/profile/', '/users/profile/edit/', '/users/achievements/',
                    '/users/education/edit/1/', '/users/certifications/', '/users/logout/']:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), '/app/', fetch_redirect_response=False)


class OldAccountPagesTest(TestCase):
    """Notifications, Settings and Change password are in the React app; behaviour is tested in users/test_api.py."""

    def test_old_pages_redirect_to_the_app(self):
        from users.models import User
        self.client.force_login(User.objects.create_user('n', password='pw'))
        for old, new in [('users:notifications', '/app/notifications'), ('users:settings', '/app/settings'),
                         ('users:change_password', '/app/settings/password')]:
            self.assertRedirects(self.client.get(reverse(old)), new, fetch_redirect_response=False)
