from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from subjects.models import ChatMessage, ChatSession, Subject
from subjects.services.rag_service import RAGService

from .test_chat_stream import CHUNK, fake_run_events, parse_sse

User = get_user_model()


class ChatSessionHistoryTest(TestCase):
    """The app's conversation list: open a past conversation and keep talking in it."""

    def setUp(self):
        self.user = User.objects.create_user('s', password='p')
        self.subject = Subject.objects.create(user=self.user, name='Databases')
        self.old = ChatSession.objects.create(user=self.user, subject=self.subject, title='Old', is_active=False, status='expired')
        ChatMessage.objects.create(session=self.old, role='user', content='old question')
        self.current = ChatSession.objects.create(user=self.user, subject=self.subject, title='Current')
        ChatMessage.objects.create(session=self.current, role='user', content='current question')
        other = User.objects.create_user('o', password='p')
        self.theirs = ChatSession.objects.create(user=other, subject=Subject.objects.create(user=other, name='X'))
        self.elsewhere = ChatSession.objects.create(user=self.user, subject=Subject.objects.create(user=self.user, name='Maths'))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.messages_url = reverse('chat-messages', args=[self.subject.id])

    def test_history_of_a_chosen_conversation(self):
        data = self.client.get(self.messages_url, {'session_id': self.old.id}).json()
        self.assertEqual([m['content'] for m in data['messages']], ['old question'])
        self.assertEqual(data['session']['id'], self.old.id)
        # without session_id it is still the active conversation, as before
        data = self.client.get(self.messages_url).json()
        self.assertEqual([m['content'] for m in data['messages']], ['current question'])

    def test_history_is_owner_and_subject_scoped(self):
        for session in (self.theirs, self.elsewhere):
            self.assertEqual(self.client.get(self.messages_url, {'session_id': session.id}).status_code, 404)
        self.assertEqual(self.client.get(self.messages_url, {'session_id': 'x'}).status_code, 400)

    @patch.object(RAGService, '_retrieve_relevant_chunks', return_value=[CHUNK])
    def test_streaming_into_a_past_conversation_resumes_it(self, _):
        with patch('reasoning.pipeline.ReasoningPipeline.run_events', fake_run_events('Answer.', ['Answer.'])):
            response = self.client.post(reverse('chat-stream', args=[self.subject.id]),
                                        {'message': 'follow up', 'session_id': self.old.id},
                                        format='json', HTTP_ACCEPT='text/event-stream')
            events = parse_sse(response)
        self.assertEqual(events[-1][0], 'done')
        self.assertEqual(events[-1][1]['session']['id'], self.old.id)
        self.assertEqual(list(self.old.messages.order_by('timestamp').values_list('content', flat=True)),
                         ['old question', 'follow up', 'Answer.'])
        self.old.refresh_from_db()
        self.current.refresh_from_db()
        self.assertTrue(self.old.is_active)
        self.assertEqual(self.old.status, 'active')
        self.assertFalse(self.current.is_active)

    def test_cannot_send_into_someone_elses_conversation(self):
        for url, kwargs in [(reverse('chat-stream', args=[self.subject.id]), {'HTTP_ACCEPT': 'text/event-stream'}),
                            (self.messages_url, {})]:
            r = self.client.post(url, {'message': 'hi', 'session_id': self.theirs.id}, format='json', **kwargs)
            self.assertEqual(r.status_code, 404)
        self.assertFalse(ChatMessage.objects.filter(content='hi').exists())
