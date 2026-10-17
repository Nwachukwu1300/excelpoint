from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from reasoning.confidence import ConfidenceScore
from reasoning.models import ReasoningSession
from reasoning.pipeline import ReasoningError, ReasoningResult
from retrieval.reranking import RankedChunk
from subjects.models import Subject
from subjects.services.rag_service import RAGService

CHUNK = {'chunk_id': 1, 'content': 'DDL stands for Data Definition Language.', 'material_name': 'db.pdf', 'similarity_score': 0.8}


def reasoning_result(subject_id, verified=True, chunks=True):
    return ReasoningResult(
        original_query='What is DDL?', subject_id=subject_id, pipeline_name='default',
        rewritten_query='DDL definition',
        retrieved_chunks=[RankedChunk(1, CHUNK['content'], 0, 1, 'db.pdf', 0.8)] if chunks else [],
        generated_answer='DDL is Data Definition Language (Source: db.pdf).',
        final_answer='DDL is Data Definition Language (Source: db.pdf).',
        confidence_score=ConfidenceScore(final_score=0.85),
        unverified_flag=not verified,
    )


class ReasoningChatTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('u', password='p')
        self.subject = Subject.objects.create(user=user, name='Databases')
        self.rag = RAGService()

    def ask(self, query, chunks=(CHUNK,), history=None):
        with patch.object(self.rag, '_retrieve_relevant_chunks', return_value=list(chunks)):
            return self.rag.generate_response(query, self.subject.id, chat_history=history)

    @patch('reasoning.pipeline.ReasoningPipeline.run')
    def test_questions_with_matches_use_reasoning_pipeline(self, run):
        run.return_value = reasoning_result(self.subject.id)
        result = self.ask('What is DDL?')

        self.assertEqual(result['response'], 'DDL is Data Definition Language (Source: db.pdf).')
        self.assertTrue(result['context_used'])
        self.assertEqual(result['metadata']['pipeline'], 'reasoning')
        self.assertEqual(result['metadata']['rewritten_query'], 'DDL definition')
        self.assertTrue(ReasoningSession.objects.filter(session_id=result['metadata']['reasoning_session_id']).exists())

    @patch('reasoning.pipeline.ReasoningPipeline.run')
    def test_unverified_answer_carries_a_warning(self, run):
        run.return_value = reasoning_result(self.subject.id, verified=False)
        self.assertIn('could not be fully verified', self.ask('What is DDL?')['response'])

    @patch('reasoning.pipeline.ReasoningPipeline.run')
    def test_pipeline_retrieving_nothing_gives_fallback(self, run):
        run.return_value = reasoning_result(self.subject.id, chunks=False)
        run.return_value.final_answer = ''
        result = self.ask('What is DDL?')
        self.assertIn("couldn't find information", result['response'])
        self.assertFalse(result['context_used'])

    @patch('reasoning.pipeline.ReasoningPipeline.run', side_effect=ReasoningError('LLM down'))
    def test_pipeline_failure_falls_back_to_single_call(self, run):
        with patch.object(self.rag, '_generate_llm_response', return_value={'content': 'DDL is Data Definition Language.'}):
            result = self.ask('What is DDL?')
        self.assertEqual(result['response'], 'DDL is Data Definition Language.')
        self.assertEqual(result['metadata']['pipeline'], 'single_call')

    @patch('reasoning.pipeline.ReasoningPipeline.run')
    def test_no_matches_and_small_talk_skip_the_pipeline(self, run):
        self.assertIn("couldn't find information", self.ask('Who painted the Mona Lisa?', chunks=())['response'])
        with patch.object(self.rag, '_generate_llm_response', return_value={'content': 'Hi! Ask me about your materials.'}):
            self.ask('Hello', chunks=())
        run.assert_not_called()

    @patch('reasoning.pipeline.ReasoningPipeline.run')
    def test_followup_without_matches_still_reaches_pipeline(self, run):
        run.return_value = reasoning_result(self.subject.id)
        self.ask('tell me more about that', chunks=(), history=[{'user': 'What is DDL?', 'assistant': 'DDL is...'}])
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs['conversation_history'][0], {'role': 'user', 'content': 'What is DDL?'})


class TraceUrlTest(TestCase):
    def test_assistant_message_links_to_its_trace(self):
        from subjects.models import ChatMessage, ChatSession
        from subjects.serializers import ChatMessageSerializer

        user = get_user_model().objects.create_user('t', password='p')
        session = ChatSession.objects.create(user=user, subject=Subject.objects.create(user=user, name='S'))
        traced = ChatMessage.objects.create(session=session, role='assistant', content='a',
                                            metadata={'model_info': {'reasoning_session_id': '7d1c2f3e-0000-4000-8000-000000000001'}})
        plain = ChatMessage.objects.create(session=session, role='assistant', content='b', metadata={})

        self.assertEqual(ChatMessageSerializer(traced).data['trace_url'], '/insights/7d1c2f3e-0000-4000-8000-000000000001/')
        self.assertIsNone(ChatMessageSerializer(plain).data['trace_url'])


class AnswerLogTest(TestCase):
    def test_every_answer_path_logs_one_json_line(self):
        import json as _json
        user = get_user_model().objects.create_user('l', password='p')
        subject = Subject.objects.create(user=user, name='Databases')
        rag = RAGService()

        with self.assertLogs('subjects.services.rag_service', level='INFO') as logs, \
                patch.object(rag, '_retrieve_relevant_chunks', return_value=[]):
            rag.generate_response('Who painted the Mona Lisa?', subject.id)

        lines = [_json.loads(m.split(':', 2)[2]) for m in logs.output if '"event": "chat_answer"' in m]
        self.assertEqual(len(lines), 1)
        self.assertEqual((lines[0]['path'], lines[0]['chunks'], lines[0]['subject_id']), ('fallback', 0, subject.id))

    @patch('reasoning.pipeline.ReasoningPipeline.run')
    def test_reasoning_answer_log_includes_trace_fields(self, run):
        import json as _json
        user = get_user_model().objects.create_user('l2', password='p')
        subject = Subject.objects.create(user=user, name='Databases')
        run.return_value = reasoning_result(subject.id)
        run.return_value.latency_breakdown = {'generation_ms': 900.0}
        rag = RAGService()

        with self.assertLogs('subjects.services.rag_service', level='INFO') as logs, \
                patch.object(rag, '_retrieve_relevant_chunks', return_value=[CHUNK]):
            rag.generate_response('What is DDL?', subject.id)

        line = next(_json.loads(m.split(':', 2)[2]) for m in logs.output if '"event": "chat_answer"' in m)
        self.assertEqual(line['path'], 'reasoning')
        self.assertTrue(line['reasoning_session_id'])
        self.assertEqual(line['stage_ms'], {'generation_ms': 900.0})
