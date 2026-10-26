from datetime import timedelta

from django.contrib.auth import get_user_model
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
