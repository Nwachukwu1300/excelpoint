import os
from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
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

    def test_signed_out_gets_a_plain_answer_and_the_csrf_cookie(self):
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'authenticated': False, 'google_sign_in': False})
        self.assertIn('csrftoken', response.cookies)
        self.assertEqual(self.client.patch('/api/me/', {'first_name': 'X'}, content_type='application/json').status_code, 403)

    def test_google_sign_in_shows_only_when_configured(self):
        with self.settings(GOOGLE_OAUTH_CLIENT_ID='id', GOOGLE_OAUTH_CLIENT_SECRET='secret'):
            self.assertTrue(self.client.get('/api/me/').json()['google_sign_in'])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/me/').json()['authenticated'], True)


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

    def test_email_cannot_be_blank_or_someone_elses(self):
        User.objects.create_user('o', email='taken@x.com', password='p')
        self.assertEqual(self.patch({'email': '   '}).json(), {'email': ['Enter an email address.']})
        self.assertEqual(self.patch({'email': 'TAKEN@x.com'}).json(), {'email': ['An account with this email already exists.']})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@x.com')

    def test_an_account_already_sharing_an_email_can_still_save(self):
        User.objects.create_user('twin', email='OLD@x.com', password='p')
        self.assertEqual(self.patch({'first_name': 'Sami'}).status_code, 200)

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

    def test_the_admin_login_shares_the_cap(self):
        User.objects.create_user('boss', password='Pass-word-123!', is_staff=True)
        for _ in range(5):
            self.client.post('/admin/login/', {'username': 'boss', 'password': 'nope'})
        self.client.post('/admin/login/', {'username': 'boss', 'password': 'Pass-word-123!'})
        self.assertNotIn('_auth_user_id', self.client.session)  # right password, still locked
        self.assertEqual(self.sign_in('boss', 'Pass-word-123!').status_code, 429)

    def test_the_api_ignores_basic_auth(self):
        import base64
        User.objects.create_user('alex', password='Pass-word-123!')
        header = 'Basic ' + base64.b64encode(b'alex:Pass-word-123!').decode()
        self.assertEqual(self.client.get('/api/notifications/', HTTP_AUTHORIZATION=header).status_code, 403)

    def test_successful_sign_ins_do_not_count_against_the_address(self):
        for i in range(25):
            User.objects.create_user(f'student{i}', password='Pass-word-123!')
            self.assertEqual(self.sign_in(f'student{i}', 'Pass-word-123!').status_code, 200)

    def test_a_forged_forwarded_for_header_does_not_dodge_the_address_cap(self):
        User.objects.create_user('alex', password='Pass-word-123!')
        for i in range(20):  # no proxy configured: X-Forwarded-For must be ignored
            self.client.post('/api/auth/login/', {'username': f'g{i}', 'password': 'x'}, content_type='application/json',
                             HTTP_X_FORWARDED_FOR=f'10.0.0.{i}')
        self.assertEqual(self.sign_in('alex', 'Pass-word-123!').status_code, 429)

    @override_settings(REST_FRAMEWORK={'NUM_PROXIES': 1})
    def test_behind_one_proxy_the_address_is_the_one_it_added(self):
        User.objects.create_user('alex', password='Pass-word-123!')
        for i in range(20):  # the client fakes the first entry; the proxy appends the real address
            self.client.post('/api/auth/login/', {'username': f'g{i}', 'password': 'x'}, content_type='application/json',
                             HTTP_X_FORWARDED_FOR=f'10.0.0.{i}, 203.0.113.7')
        blocked = self.client.post('/api/auth/login/', {'username': 'alex', 'password': 'Pass-word-123!'},
                                   content_type='application/json', HTTP_X_FORWARDED_FOR='203.0.113.7')
        self.assertEqual(blocked.status_code, 429)
        other = self.client.post('/api/auth/login/', {'username': 'alex', 'password': 'Pass-word-123!'},
                                 content_type='application/json', HTTP_X_FORWARDED_FOR='198.51.100.2')
        self.assertEqual(other.status_code, 200)

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
        self.assertIs(self.client.get('/api/me/').json()['authenticated'], False)

    def test_register_refuses_an_email_already_in_use(self):
        User.objects.create_user('alex', email='alex@example.com', password='Pass-word-123!')
        r = self.post('/api/auth/register/', {'username': 'alex2', 'email': 'ALEX@example.com',
                                              'password1': 'Pass-word-123!', 'password2': 'Pass-word-123!'})
        self.assertEqual(r.json(), {'email': ['An account with this email already exists.']})

    def test_weak_password_errors_are_shown_under_the_password(self):
        r = self.post('/api/auth/register/', {'username': 'new', 'email': 'n@example.com', 'password1': 'abc', 'password2': 'abc'}).json()
        self.assertIn('too short', r['password1'][0])
        self.assertNotIn('password2', r)
        r = self.post('/api/auth/register/', {'username': 'new', 'email': 'n@example.com', 'password1': 'Pass-word-123!', 'password2': 'other'}).json()
        self.assertIn('password2', r)  # a mismatch stays on the repeat field

    def test_spelling_variants_share_one_lockout(self):
        User.objects.create_user('Alex', password='Pass-word-123!')
        for variant in ['alex', 'ALEX', 'aLeX', 'AlEx', 'alEX']:
            self.assertEqual(self.sign_in(variant, 'nope').status_code, 400)
        self.assertEqual(self.sign_in('Alex', 'Pass-word-123!').status_code, 429)

    def test_sign_in_ignores_username_case(self):
        User.objects.create_user('QA_Breaker', password='Pass-word-123!')
        self.assertEqual(self.sign_in('qa_breaker', 'Pass-word-123!').status_code, 200)

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


import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import override_settings

from reasoning.models import ReasoningSession
from subjects.models import ChatSession, Subject, SubjectMaterial

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class DeleteAccountTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user('s', password='Pass-word-123!')
        self.other = User.objects.create_user('o', password='Pass-word-123!')
        self.subject = Subject.objects.create(user=self.user, name='Bio')
        self.material = SubjectMaterial(subject=self.subject, file_type='PDF', status='COMPLETED')
        self.material.file.save('notes.pdf', ContentFile(b'%PDF'))
        ChatSession.objects.create(user=self.user, subject=self.subject)
        ReasoningSession.objects.create(subject_id=self.subject.id, original_query='What is DNA?', pipeline_name='p', total_latency=1)
        kept = Subject.objects.create(user=self.other, name='Kept')
        ReasoningSession.objects.create(subject_id=kept.id, original_query='other', pipeline_name='p', total_latency=1)
        self.client.force_login(self.user)

    def delete(self, confirm):
        return self.client.post('/api/me/delete/', {'confirm': confirm}, content_type='application/json')

    def test_wrong_password_deletes_nothing(self):
        self.assertEqual(self.delete('nope').json(), {'confirm': ['That password isn’t right.']})
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_deletes_the_account_files_and_traces_then_signs_out(self):
        path = self.material.file.path
        self.assertEqual(self.delete('Pass-word-123!').status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Subject.objects.filter(pk=self.subject.pk).exists())
        self.assertFalse(os.path.exists(path))
        self.assertEqual(list(ReasoningSession.objects.values_list('original_query', flat=True)), ['other'])
        self.assertIs(self.client.get('/api/me/').json()['authenticated'], False)
        self.assertTrue(User.objects.filter(pk=self.other.pk).exists())

    def test_google_only_accounts_confirm_with_their_username(self):
        self.user.set_unusable_password()
        self.user.save()
        self.client.force_login(self.user)
        self.assertEqual(self.delete('wrong').status_code, 400)
        self.assertEqual(self.delete('S').status_code, 204)

    def test_signed_out_cannot_delete(self):
        self.client.logout()
        self.assertEqual(self.delete('Pass-word-123!').status_code, 403)

    def test_deleting_a_subject_removes_its_files_and_traces_but_only_yours(self):
        path = self.material.file.path
        self.client.force_login(self.other)
        self.assertEqual(self.client.delete(f'/api/subjects/{self.subject.id}/').status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.delete(f'/api/subjects/{self.subject.id}/').status_code, 204)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(ReasoningSession.objects.count(), 1)


@override_settings(MEDIA_ROOT=MEDIA)
class ExportDataTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s', email='s@x.com', password='Pass-word-123!')
        other = User.objects.create_user('o', password='p')
        subject = Subject.objects.create(user=self.user, name='Bio/../Logy')
        material = SubjectMaterial(subject=subject, file_type='PDF', status='COMPLETED', original_name='../notes.pdf')
        material.file.save('notes.pdf', ContentFile(b'%PDF-my-notes'))
        from subjects.models import ChatMessage, ContentChunk, Flashcard
        ContentChunk.objects.create(material=material, content='Chlorophyll absorbs red light.', chunk_index=0)
        Flashcard.objects.create(subject=subject, material=material, question='What does chlorophyll absorb?', answer='Red and blue light.')
        chat = ChatSession.objects.create(user=self.user, subject=subject, title='Light')
        ChatMessage.objects.create(session=chat, role='user', content='What does chlorophyll absorb?')
        Subject.objects.create(user=other, name='Not mine')

    def test_zip_has_my_data_and_files_only(self):
        import io
        import json as _json
        import zipfile
        self.client.force_login(self.user)
        response = self.client.get('/api/me/export/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        zf = zipfile.ZipFile(io.BytesIO(b''.join(response.streaming_content)))
        data = _json.loads(zf.read('data.json'))
        self.assertEqual(data['account']['email'], 's@x.com')
        self.assertEqual([s['name'] for s in data['subjects']], ['Bio/../Logy'])
        exported = data['subjects'][0]['files'][0]
        self.assertEqual(exported['text'], 'Chlorophyll absorbs red light.')
        self.assertEqual(zf.read(exported['file_in_zip']), b'%PDF-my-notes')
        self.assertTrue(all('..' not in n.split('/') and not n.startswith('/') for n in zf.namelist()))
        self.assertEqual(data['subjects'][0]['flashcards'][0]['question'], 'What does chlorophyll absorb?')
        self.assertEqual(data['conversations'][0]['messages'][0]['text'], 'What does chlorophyll absorb?')

    def test_signed_out_cannot_export(self):
        self.assertEqual(self.client.get('/api/me/export/').status_code, 403)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class PasswordResetTest(TestCase):
    def setUp(self):
        cache.clear()
        from config.celery import app
        app.conf.task_always_eager = True  # run the email task in the test, as the worker would
        self.addCleanup(setattr, app.conf, 'task_always_eager', False)
        self.user = User.objects.create_user('alex', email='alex@example.com', password='Old-pass-123!')

    def post(self, url, body):
        return self.client.post(url, body, content_type='application/json')

    def link_parts(self):
        from django.core import mail
        import re as _re
        uid, token = _re.search(r'/app/reset-password/([^/\s]+)/([^/\s]+)', mail.outbox[-1].body).groups()
        return uid, token

    def test_sends_a_working_link_that_signs_you_in_once(self):
        from django.core import mail
        r = self.post('/api/auth/password-reset/', {'email': 'ALEX@example.com'})
        self.assertEqual(r.json()['ok'], True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alex@example.com'])
        self.assertIn('username: alex', mail.outbox[0].body)
        uid, token = self.link_parts()
        body = {'uid': uid, 'token': token, 'new_password1': 'Brand-new-456!', 'new_password2': 'Brand-new-456!'}
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', body).json()['ok'], True)
        self.assertIs(self.client.get('/api/me/').json()['authenticated'], True)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Brand-new-456!'))
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', body).status_code, 400)  # used once

    def test_unknown_email_gets_the_same_answer_and_no_email(self):
        from django.core import mail
        known = self.post('/api/auth/password-reset/', {'email': 'alex@example.com'}).json()
        unknown = self.post('/api/auth/password-reset/', {'email': 'nobody@example.com'}).json()
        self.assertEqual(known, unknown)
        self.assertEqual(len(mail.outbox), 1)

    def test_a_mail_failure_gives_the_same_answer(self):
        with patch('users.auth_api.send_password_reset.delay', side_effect=ConnectionError('broker down')):
            r = self.post('/api/auth/password-reset/', {'email': 'alex@example.com'})
        self.assertEqual((r.status_code, r.json()['ok']), (200, True))

    def test_requests_per_email_are_limited(self):
        from django.core import mail
        for _ in range(5):
            self.assertEqual(self.post('/api/auth/password-reset/', {'email': 'alex@example.com'}).status_code, 200)
        self.assertEqual(len(mail.outbox), 3)

    def test_bad_token_and_weak_password_are_refused(self):
        self.post('/api/auth/password-reset/', {'email': 'alex@example.com'})
        uid, token = self.link_parts()
        bad = self.post('/api/auth/password-reset/confirm/', {'uid': uid, 'token': 'nope', 'new_password1': 'Brand-new-456!', 'new_password2': 'Brand-new-456!'})
        self.assertIn('expired', bad.json()['detail'])
        weak = self.post('/api/auth/password-reset/confirm/', {'uid': uid, 'token': token, 'new_password1': 'abc', 'new_password2': 'abc'})
        self.assertIn('too short', weak.json()['new_password1'][0])
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', {'uid': '!!', 'token': token}).status_code, 400)
