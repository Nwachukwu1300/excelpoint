from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from subjects.models import Flashcard, FlashcardReview, Subject
from users.models import Notification

User = get_user_model()


class MeApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s', email='s@x.com', password='p', first_name='Sam')
        self.other = User.objects.create_user('o', password='p')
        self.db = Subject.objects.create(user=self.user, name='Databases')
        self.maths = Subject.objects.create(user=self.user, name='Maths')
        Subject.objects.create(user=self.other, name='Secret')
        new = Flashcard.objects.create(subject=self.db, question='q1', answer='a1')
        later = Flashcard.objects.create(subject=self.db, question='q2', answer='a2')
        FlashcardReview.objects.create(user=self.user, flashcard=later, due_at=timezone.now() + timedelta(days=3))
        Flashcard.objects.create(subject=Subject.objects.get(name='Secret'), question='x', answer='y')
        Notification.notify(self.user, 'material_ready', 'notes.pdf is ready')
        Notification.notify(self.other, 'material_ready', 'not yours')
        self.new = new

    def test_returns_own_user_counts_and_subjects(self):
        self.client.force_login(self.user)
        data = self.client.get('/api/me/').json()
        self.assertEqual(data['username'], 's')
        self.assertEqual(data['first_name'], 'Sam')
        self.assertEqual(data['unread_notifications'], 1)
        self.assertEqual(data['due_count'], 1)  # q1 is new; q2 is not due for 3 days
        self.assertEqual(data['subjects'], [
            {'id': self.db.id, 'name': 'Databases', 'due_count': 1},
            {'id': self.maths.id, 'name': 'Maths', 'due_count': 0},
        ])

    def test_sets_csrf_cookie_even_when_anonymous(self):
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, 403)
        self.assertIn('csrftoken', response.cookies)


class NotificationsApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s', password='p')
        self.other = User.objects.create_user('o', password='p')
        self.a = Notification.notify(self.user, 'material_ready', 'a.pdf is ready', url='/subjects/1/')
        self.b = Notification.notify(self.user, 'review_due', '3 cards due')
        self.theirs = Notification.notify(self.other, 'review_due', 'not yours')

    def test_lists_only_own_newest_first(self):
        self.client.force_login(self.user)
        data = self.client.get('/api/notifications/?limit=5').json()
        self.assertEqual(data['unread'], 2)
        self.assertEqual([n['title'] for n in data['results']], ['3 cards due', 'a.pdf is ready'])
        self.assertEqual(data['results'][1]['url'], '/subjects/1/')
        self.assertFalse(data['results'][0]['read'])

    def test_bad_limit_is_400(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/notifications/?limit=x').status_code, 400)

    def test_mark_some_then_all_read(self):
        self.client.force_login(self.user)
        r = self.client.post('/api/notifications/read/', {'ids': [self.a.id, self.theirs.id]}, content_type='application/json')
        self.assertEqual(r.json(), {'marked': 1, 'unread': 1})
        r = self.client.post('/api/notifications/read/', {}, content_type='application/json')
        self.assertEqual(r.json(), {'marked': 1, 'unread': 0})
        self.theirs.refresh_from_db()
        self.assertIsNone(self.theirs.read_at)  # other users' notifications are never touched

    def test_mark_read_rejects_bad_ids(self):
        self.client.force_login(self.user)
        r = self.client.post('/api/notifications/read/', {'ids': 'all'}, content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_anonymous_is_403(self):
        self.assertEqual(self.client.get('/api/notifications/').status_code, 403)
        self.assertEqual(self.client.post('/api/notifications/read/').status_code, 403)

    def test_mark_read_enforces_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        r = client.post('/api/notifications/read/', {}, content_type='application/json')
        self.assertEqual(r.status_code, 403)
        client.get('/api/me/')  # sets the csrftoken cookie, like the app does on load
        token = client.cookies['csrftoken'].value
        r = client.post('/api/notifications/read/', {}, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)


class SettingsApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s', email='old@x.com', password='Old-pass-123!', first_name='Sam')
        self.client.force_login(self.user)

    def patch(self, body):
        return self.client.patch('/api/me/', body, content_type='application/json')

    def test_saves_names_email_and_education(self):
        data = self.patch({'first_name': 'Samira', 'email': 'new@x.com', 'education_level': 'undergraduate'}).json()
        self.assertEqual((data['first_name'], data['last_name'], data['email'], data['education_level']), ('Samira', '', 'new@x.com', 'undergraduate'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@x.com')
        self.assertIn({'value': 'undergraduate', 'label': 'Undergraduate'}, data['education_choices'])
        # fields left out keep their value
        self.assertEqual(self.patch({'last_name': 'K'}).json()['first_name'], 'Samira')

    def test_rejects_a_bad_email_or_level(self):
        r = self.patch({'email': 'not-an-email'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.json())
        self.assertIn('education_level', self.patch({'education_level': 'wizard'}).json())

    def test_change_password_keeps_you_signed_in(self):
        r = self.client.post('/api/me/password/', {'old_password': 'Old-pass-123!', 'new_password1': 'Brand-new-456!',
                                                   'new_password2': 'Brand-new-456!'}, content_type='application/json')
        self.assertEqual(r.json(), {'ok': True})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Brand-new-456!'))
        self.assertEqual(self.client.get('/api/me/').status_code, 200)  # session survived

    def test_change_password_errors(self):
        r = self.client.post('/api/me/password/', {'old_password': 'wrong', 'new_password1': 'short', 'new_password2': 'other'},
                             content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('old_password', r.json())
        self.assertIn('new_password2', r.json())

    def test_missing_new_password_does_not_lock_the_account(self):
        r = self.client.post('/api/me/password/', {'old_password': 'Old-pass-123!'}, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Old-pass-123!'))

    def test_google_only_accounts_set_a_password_without_the_old_one(self):
        self.user.set_unusable_password()
        self.user.save()
        self.client.force_login(self.user)
        self.assertFalse(self.client.get('/api/me/').json()['has_password'])
        r = self.client.post('/api/me/password/', {'new_password1': 'Brand-new-456!', 'new_password2': 'Brand-new-456!'},
                             content_type='application/json')
        self.assertEqual(r.json(), {'ok': True})


class AuthApiTest(TestCase):
    def setUp(self):
        cache.clear()  # failed sign-in counts live in the cache, which outlives each test

    def post(self, url, body, client=None):
        return (client or self.client).post(url, body, content_type='application/json')

    def sign_in(self, username, password):
        return self.post('/api/auth/login/', {'username': username, 'password': password})

    def test_too_many_wrong_passwords_lock_that_username_only(self):
        User.objects.create_user('alex', password='Pass-word-123!')
        User.objects.create_user('sam', password='Pass-word-123!')
        for _ in range(5):
            self.assertEqual(self.sign_in('alex', 'nope').status_code, 400)
        locked = self.sign_in('ALEX', 'Pass-word-123!')  # right password, other casing: still locked
        self.assertEqual(locked.status_code, 429)
        self.assertEqual(locked['Retry-After'], '900')
        self.assertIn('Too many', locked.json()['detail'])
        self.assertEqual(self.sign_in('sam', 'Pass-word-123!').status_code, 200)

    def test_signing_in_clears_the_username_count(self):
        User.objects.create_user('alex', password='Pass-word-123!')
        for _ in range(4):
            self.sign_in('alex', 'nope')
        self.assertEqual(self.sign_in('alex', 'Pass-word-123!').status_code, 200)
        for _ in range(4):
            self.assertEqual(self.sign_in('alex', 'nope').status_code, 400)

    def test_too_many_failures_from_one_address_lock_it(self):
        User.objects.create_user('alex', password='Pass-word-123!')
        for i in range(20):
            self.sign_in(f'guess{i}', 'nope')
        self.assertEqual(self.sign_in('alex', 'Pass-word-123!').status_code, 429)

    def test_sign_in_and_out(self):
        User.objects.create_user('alex', password='Pass-word-123!')
        self.assertEqual(self.post('/api/auth/login/', {'username': 'alex', 'password': 'nope'}).status_code, 400)
        r = self.post('/api/auth/login/', {'username': ' alex ', 'password': 'Pass-word-123!'})
        self.assertEqual(r.json()['ok'], True)
        self.assertEqual(self.client.get('/api/me/').json()['username'], 'alex')
        self.post('/api/auth/logout/', {})
        self.assertEqual(self.client.get('/api/me/').status_code, 403)

    def test_register_validates_then_signs_you_in(self):
        r = self.post('/api/auth/register/', {'username': 'new', 'email': 'bad', 'password1': '123', 'password2': '456'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.json())
        self.assertIn('password2', r.json())
        r = self.post('/api/auth/register/', {'username': 'new', 'email': 'new@x.com', 'password1': 'Brand-new-456!', 'password2': 'Brand-new-456!'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get('/api/me/').json()['email'], 'new@x.com')
        again = self.post('/api/auth/register/', {'username': 'new', 'email': 'n2@x.com', 'password1': 'Brand-new-456!', 'password2': 'Brand-new-456!'})
        self.assertIn('username', again.json())  # taken

    def test_auth_endpoints_require_the_csrf_token(self):
        User.objects.create_user('alex', password='Pass-word-123!')
        client = Client(enforce_csrf_checks=True)
        body = {'username': 'alex', 'password': 'Pass-word-123!'}
        self.assertEqual(self.post('/api/auth/login/', body, client).status_code, 403)  # no token: blocked even when signed out
        client.get('/api/me/')  # sets csrftoken, as the app's first request does
        r = client.post('/api/auth/login/', body, content_type='application/json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(r.status_code, 200)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get('/api/auth/login/').status_code, 405)
