from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from retrieval.pipeline import PipelineConfig, PipelineManager
from subjects.models import Subject

from .models import ReasoningSession


def make_session(subject):
    return ReasoningSession.objects.create(
        original_query='q', classification_category='retrieval_required',
        pipeline_name='default', generated_answer='a', final_answer='a',
        total_latency=1.0, subject_id=subject.id,
    )


class SubjectOwnershipTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user('owner', password='p')
        self.other = User.objects.create_user('other', password='p')
        self.subject = Subject.objects.create(user=self.owner, name='Private')
        self.session = make_session(self.subject)
        self.client = APIClient()
        self.client.force_authenticate(self.other)

    @patch('reasoning.views.ReasoningPipeline')
    def test_reasoning_query_on_someone_elses_subject_is_404(self, pipeline):
        response = self.client.post(
            reverse('reasoning:query'), {'query': 'hi', 'subject_id': self.subject.id}, format='json'
        )
        self.assertEqual(response.status_code, 404)
        pipeline.assert_not_called()

    @patch('retrieval.views.PipelineManager.get_pipeline')
    def test_retrieval_query_on_someone_elses_subject_is_404(self, get_pipeline):
        PipelineManager.create_pipeline(PipelineConfig(name='default'))
        response = self.client.post(
            reverse('retrieval:query'),
            {'pipeline_name': 'default', 'query': 'hi', 'subject_id': self.subject.id}, format='json',
        )
        self.assertEqual(response.status_code, 404)
        get_pipeline.assert_not_called()

    def test_sessions_and_stats_hide_other_users_sessions(self):
        listing = self.client.get(reverse('reasoning:session-list')).json()
        self.assertNotIn(str(self.session.session_id), str(listing))

        for name in ('reasoning:session-detail', 'reasoning:session-chunks'):
            response = self.client.get(reverse(name, args=[self.session.session_id]))
            self.assertEqual(response.status_code, 404, name)

        stats = self.client.get(reverse('reasoning:stats')).json()
        self.assertEqual(stats.get('total_sessions'), 0)

    def test_owner_still_sees_their_session(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse('reasoning:session-detail', args=[self.session.session_id]))
        self.assertEqual(response.status_code, 200)

    def test_retrieval_admin_endpoints_need_staff(self):
        self.assertEqual(self.client.get(reverse('retrieval:pipeline-list-create')).status_code, 403)
