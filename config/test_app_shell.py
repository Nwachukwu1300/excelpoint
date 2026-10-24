import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from config import views


class AppShellTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('s', password='p')
        self.index = Path(tempfile.mkdtemp()) / 'index.html'
        self.index.write_text('<div id="root"></div>')

    def test_anonymous_redirects_to_login(self):
        response = self.client.get('/app/subjects/3')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login/?next=/app/subjects/3', response['Location'])

    def test_serves_built_index_for_any_app_route_with_csrf_cookie(self):
        self.client.force_login(self.user)
        with patch.object(views, 'APP_INDEX', self.index):
            for url in ['/app', '/app/', '/app/subjects/3/chat']:
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, url)
                self.assertContains(response, '<div id="root">')
        self.assertIn('csrftoken', response.cookies)

    def test_missing_build_is_503(self):
        self.client.force_login(self.user)
        with patch.object(views, 'APP_INDEX', self.index.with_name('missing.html')):
            self.assertEqual(self.client.get('/app/').status_code, 503)
