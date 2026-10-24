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
        self.assertRedirects(response, reverse('users:login'), fetch_redirect_response=False)
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


class NotificationTest(TestCase):
    def setUp(self):
        from users.models import User
        self.user = User.objects.create_user('n', password='pw')
        self.client.force_login(self.user)

    def note(self, url='/subjects/', user=None):
        from users.models import Notification
        return Notification.notify(user or self.user, 'material_ready', 'Notes ready', url=url)

    def test_bell_shows_unread_count(self):
        self.note(); self.note()
        html = self.client.get(reverse('users:notifications')).content.decode()
        self.assertIn('2 unread', html)

    def test_opening_marks_read_and_follows_internal_link(self):
        n = self.note('/subjects/3/')
        response = self.client.post(reverse('users:open_notification', args=[n.id]))
        self.assertRedirects(response, '/subjects/3/', fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertIsNotNone(n.read_at)

    def test_external_links_are_not_followed(self):
        for url in ['https://evil.example', '//evil.example']:
            n = self.note(url)
            response = self.client.post(reverse('users:open_notification', args=[n.id]))
            self.assertRedirects(response, reverse('users:notifications'), fetch_redirect_response=False)

    def test_cannot_open_someone_elses(self):
        from users.models import User
        other = self.note(user=User.objects.create_user('o2', password='pw'))
        self.assertEqual(self.client.post(reverse('users:open_notification', args=[other.id])).status_code, 404)

    def test_mark_all_read(self):
        self.note(); self.note()
        self.client.post(reverse('users:notifications'))
        self.assertFalse(self.user.notifications.filter(read_at__isnull=True).exists())


class ChangePasswordTest(TestCase):
    url = reverse('users:change_password')
    NEW = 'Correct-Horse-Battery-9'

    def setUp(self):
        from users.models import User
        self.user = User.objects.create_user('cp', 'cp@x.com', 'Old-Password-123')
        self.client.force_login(self.user)

    def post(self, **data):
        return self.client.post(self.url, data)

    def test_page_renders_the_form(self):
        self.assertContains(self.client.get(self.url), 'name="old_password"')

    def test_wrong_old_password_or_weak_new_one_is_rejected(self):
        self.post(old_password='wrong', new_password1=self.NEW, new_password2=self.NEW)
        self.post(old_password='Old-Password-123', new_password1='a', new_password2='a')
        self.post(old_password='Old-Password-123')  # missing new password used to lock the account
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Old-Password-123'))

    def test_change_keeps_the_user_logged_in(self):
        response = self.post(old_password='Old-Password-123', new_password1=self.NEW, new_password2=self.NEW)
        self.assertRedirects(response, reverse('users:settings'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW))
        self.assertEqual(self.client.get(reverse('users:settings')).status_code, 200)  # session survived

    def test_google_only_account_sets_a_password_without_an_old_one(self):
        self.user.set_unusable_password()
        self.user.save()
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(self.url), 'name="old_password"')
        self.post(new_password1=self.NEW, new_password2=self.NEW)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW))
