import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from reasoning.pipeline import ReasoningResult
from retrieval.reranking import RankedChunk
from subjects.models import ChatMessage, Subject
from subjects.services.rag_service import RAGService

CHUNK = {'chunk_id': 1, 'content': 'DML includes INSERT.', 'material_name': 'db.pdf', 'similarity_score': 0.8}


def parse_sse(response):
    body = b''.join(response.streaming_content).decode()
    events = []
    for block in body.strip().split('\n\n'):
        lines = dict(line.split(': ', 1) for line in block.split('\n'))
        events.append((lines['event'], json.loads(lines['data'])))
    return events


def fake_run_events(final_answer, tokens):
    def run_events(self, **kwargs):
        for t in tokens:
            yield ('token', t)
        yield ('result', ReasoningResult(
            original_query=kwargs['query'], subject_id=kwargs['subject_id'], pipeline_name='default',
            retrieved_chunks=[RankedChunk(1, CHUNK['content'], 0, 1, 'db.pdf', 0.8)],
            generated_answer=''.join(tokens), final_answer=final_answer,
        ))
    return run_events


class ChatStreamTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('s', password='p')
        self.subject = Subject.objects.create(user=self.user, name='Databases')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse('chat-stream', args=[self.subject.id])

    def post(self, message='What is INSERT?'):
        # Send the Accept header a browser's fetch() sends; without the SSE renderer DRF answers 406
        return self.client.post(self.url, {'message': message}, format='json', HTTP_ACCEPT='text/event-stream')

    @patch.object(RAGService, '_retrieve_relevant_chunks', return_value=[CHUNK])
    def test_tokens_then_done_with_saved_message(self, _):
        # The body streams lazily, so it must be read while the patch is active
        with patch('reasoning.pipeline.ReasoningPipeline.run_events', fake_run_events('INSERT is DML.', ['INSERT ', 'is DML.'])):
            response = self.post()
            events = parse_sse(response)

        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual([e for e, _ in events], ['token', 'token', 'done'])
        self.assertEqual(''.join(d['text'] for e, d in events if e == 'token'), 'INSERT is DML.')
        done = events[-1][1]
        self.assertEqual(done['assistant_message']['content'], 'INSERT is DML.')
        self.assertTrue(done['assistant_message']['trace_url'])
        self.assertEqual(ChatMessage.objects.filter(session__subject=self.subject).count(), 2)
        from reasoning.models import ReasoningSession
        self.assertEqual(ReasoningSession.objects.filter(subject_id=self.subject.id).count(), 1)  # one trace per question

    @patch.object(RAGService, '_retrieve_relevant_chunks', return_value=[CHUNK])
    def test_done_carries_retry_answer_that_replaces_streamed_text(self, _):
        with patch('reasoning.pipeline.ReasoningPipeline.run_events',
                   fake_run_events('Verified retry answer.', ['first ', 'draft'])):
            events = parse_sse(self.post())
        self.assertEqual(events[-1][1]['assistant_message']['content'], 'Verified retry answer.')

    @patch.object(RAGService, '_retrieve_relevant_chunks', return_value=[])
    def test_no_match_streams_the_fallback(self, _):
        events = parse_sse(self.post('Who painted the Mona Lisa?'))
        self.assertEqual([e for e, _ in events], ['token', 'done'])
        self.assertIn("couldn't find information", events[0][1]['text'])

    def test_failure_becomes_an_error_event(self):
        with patch.object(RAGService, 'respond_events', side_effect=RuntimeError('boom')):
            events = parse_sse(self.post())
        self.assertEqual(events, [('error', {'message': 'XP is currently unavailable. Please try again later.'})])

    def test_access_control(self):
        other = Subject.objects.create(user=get_user_model().objects.create_user('o', password='p'), name='X')
        self.assertEqual(self.client.post(reverse('chat-stream', args=[other.id]), {'message': 'hi'}, format='json').status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.post().status_code, (401, 403))
        self.assertEqual(self.client.get(self.url).status_code, 403)

    @patch.object(RAGService, '_retrieve_relevant_chunks', return_value=[CHUNK])
    def test_pipeline_finding_nothing_still_streams_the_fallback(self, _):
        def nothing_found(self, **kwargs):
            yield ('result', ReasoningResult(original_query=kwargs['query'], subject_id=kwargs['subject_id'],
                                             pipeline_name='default', unverified_flag=True))
        with patch('reasoning.pipeline.ReasoningPipeline.run_events', nothing_found):
            events = parse_sse(self.post())
        self.assertEqual([e for e, _ in events], ['token', 'done'])
        self.assertIn("couldn't find information", events[0][1]['text'])

    def test_invalid_input_is_a_json_400_even_when_asking_for_a_stream(self):
        response = self.client.post(self.url, {}, format='json', HTTP_ACCEPT='text/event-stream')
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', json.loads(response.content))


from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle

FAKE_ANSWER = {'response': 'ok', 'retrieved_chunks': [], 'context_used': False, 'response_time': 0.1,
               'metadata': {'pipeline': 'fallback'}}


@patch.dict(ScopedRateThrottle.THROTTLE_RATES, {'llm': '2/min'})
@patch.object(RAGService, 'generate_response', return_value=FAKE_ANSWER)
class LLMRateLimitTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user('rl', password='p')
        self.subject = Subject.objects.create(user=self.user, name='S')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def send(self):
        return self.client.post(reverse('chat-messages', args=[self.subject.id]), {'message': 'hi'}, format='json')

    def test_sending_is_capped_per_user(self, _):
        self.assertEqual([self.send().status_code for _ in range(3)], [201, 201, 429])
        # the stream endpoint shares the same budget
        self.assertEqual(self.client.post(reverse('chat-stream', args=[self.subject.id]), {'message': 'hi'},
                                          format='json', HTTP_ACCEPT='text/event-stream').status_code, 429)

    def test_reading_history_is_not_limited(self, _):
        self.send(); self.send()
        self.assertEqual(self.client.get(reverse('chat-messages', args=[self.subject.id])).status_code, 200)

    def test_each_user_has_their_own_budget(self, _):
        self.send(); self.send()
        other = get_user_model().objects.create_user('rl2', password='p')
        self.client.force_authenticate(other)
        subject = Subject.objects.create(user=other, name='T')
        self.assertEqual(self.client.post(reverse('chat-messages', args=[subject.id]), {'message': 'hi'},
                                          format='json').status_code, 201)
