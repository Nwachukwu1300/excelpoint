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

    def test_verified_email_creates_user(self):
        user = GoogleOAuthService().authenticate_or_create_user(
            {'email': 'a@x.com', 'sub': '1', 'email_verified': True, 'given_name': 'A'}
        )
        self.assertEqual(user.email, 'a@x.com')


class EditProfileTest(TestCase):
    def test_edit_saves_user_fields_and_redirects_to_profile(self):
        from users.models import User
        user = User.objects.create_user('p', 'old@x.com', 'pw')
        self.client.force_login(user)

        response = self.client.post(reverse('users:edit_profile'), {
            'first_name': 'New', 'last_name': 'Name', 'email': 'new@x.com',
            'current_role': 'Dev', 'experience_level': 'entry', 'bio': '',
            'linkedin_profile': '', 'github_profile': '',
        })

        self.assertRedirects(response, reverse('users:profile'), fetch_redirect_response=False)
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.email), ('New', 'new@x.com'))


class OldAccountPagesTest(TestCase):
    """Notifications, Settings and Change password are in the React app; behaviour is tested in users/test_api.py."""

    def test_old_pages_redirect_to_the_app(self):
        from users.models import User
        self.client.force_login(User.objects.create_user('n', password='pw'))
        for old, new in [('users:notifications', '/app/notifications'), ('users:settings', '/app/settings'),
                         ('users:change_password', '/app/settings/password')]:
            self.assertRedirects(self.client.get(reverse(old)), new, fetch_redirect_response=False)
