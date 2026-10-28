import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from config import views
from subjects.models import Subject


class AppShellTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('s', password='p')
        self.index = Path(tempfile.mkdtemp()) / 'index.html'
        self.index.write_text('<div id="root"></div>')

    def test_anonymous_redirects_to_login(self):
        response = self.client.get('/app/subjects/3')
        self.assertRedirects(response, '/app/login?next=/app/subjects/3', fetch_redirect_response=False)

    def test_sign_in_register_and_landing_are_public(self):
        with patch.object(views, 'APP_INDEX', self.index):
            for url in ['/app/login', '/app/register', '/app/welcome', '/app/privacy']:
                self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertRedirects(self.client.get('/'), '/app/welcome', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/users/login/?next=/app/review'), '/app/login?next=/app/review', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/users/register/'), '/app/register', fetch_redirect_response=False)

    def test_serves_built_index_for_any_app_route_with_csrf_cookie(self):
        self.client.force_login(self.user)
        with patch.object(views, 'APP_INDEX', self.index):
            for url in ['/app', '/app/', '/app/subjects/3/chat']:
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, url)
                self.assertContains(response, '<div id="root">')
        self.assertIn('csrftoken', response.cookies)

    def test_signed_in_home_goes_to_the_app(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get('/'), '/app', fetch_redirect_response=False)

    def test_login_lands_in_the_app_or_a_safe_next(self):
        login = lambda **extra: self.client.post('/api/auth/login/', {'username': 's', 'password': 'p', **extra},
                                                 content_type='application/json').json()
        self.assertEqual(login(), {'ok': True, 'next': '/app/'})
        self.assertEqual(login(next='/app/subjects/3')['next'], '/app/subjects/3')
        for evil in ['https://evil.example/', '//evil.example/']:
            self.assertEqual(login(next=evil)['next'], '/app/')

    def test_missing_build_is_503(self):
        self.client.force_login(self.user)
        with patch.object(views, 'APP_INDEX', self.index.with_name('missing.html')):
            self.assertEqual(self.client.get('/app/').status_code, 503)


class SubjectsCutoverTest(TestCase):
    def test_old_subject_pages_redirect_to_the_app(self):
        user = get_user_model().objects.create_user('s', password='p')
        subject = Subject.objects.create(user=user, name='DB')
        self.client.force_login(user)
        for old in ['/subjects/', '/api/']:
            self.assertRedirects(self.client.get(old), '/app/subjects', fetch_redirect_response=False)
        for old in [f'/subjects/{subject.id}/', f'/api/{subject.id}/']:
            self.assertRedirects(self.client.get(old), f'/app/subjects/{subject.id}', fetch_redirect_response=False)

    def test_old_quiz_pages_redirect_to_the_app(self):
        user = get_user_model().objects.create_user('q', password='p')
        self.client.force_login(user)
        cases = {
            '/api/quiz/9/take/': '/app/quizzes/9/start',
            '/api/quiz/9/take/?dynamic=true': '/app/quizzes/9/start?fresh=1',
            '/api/quiz/results/5/': '/app/quiz-attempts/5/results',
            '/api/quiz/attempt/5/detail/': '/app/quiz-attempts/5/results',
            '/api/quiz/history/': '/app/quizzes/history',
        }
        for old, new in cases.items():
            self.assertRedirects(self.client.get(old), new, fetch_redirect_response=False)
        # the old poll that sent correct answers to the browser no longer exists
        self.assertEqual(self.client.get('/api/quiz/attempt/5/check-questions/').status_code, 404)
