from unittest.mock import MagicMock, patch

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


from reasoning.pipeline import ReasoningPipeline
from reasoning.rewriter import RewriteResult




class StrictPipelineTest(TestCase):
    """The pipeline must never answer without retrieved materials, and only rewrites follow-ups."""

    def _pipeline(self, chunks):
        p = ReasoningPipeline()
        p._rewrite_query = MagicMock(return_value=(RewriteResult('q', 'rewritten q', [], 0, ''), 0.0))
        p._retrieve_chunks = MagicMock(return_value=(chunks, 0.0, {}))
        return p

    def test_standalone_question_is_searched_as_typed(self):
        p = self._pipeline([])
        result = p.run('What is DDL?', subject_id=1)
        p._rewrite_query.assert_not_called()
        self.assertEqual(p._retrieve_chunks.call_args.args[0], 'What is DDL?')
        self.assertEqual(ReasoningSession.create_from_result(result).classification_category, 'standalone')

    def test_follow_up_is_rewritten_with_history(self):
        p = self._pipeline([])
        history = [{'role': 'user', 'content': 'What is DML?'}]
        result = p.run('Give an example of it', subject_id=1, conversation_history=history)
        p._rewrite_query.assert_called_once_with('Give an example of it', history)
        self.assertEqual(p._retrieve_chunks.call_args.args[0], 'rewritten q')
        self.assertEqual(ReasoningSession.create_from_result(result).classification_category, 'follow_up')

    def test_caller_can_skip_rewrite_even_with_history(self):
        p = self._pipeline([])
        p.run('What is 3NF?', subject_id=1, conversation_history=[{'role': 'user', 'content': 'hi'}], rewrite=False)
        p._rewrite_query.assert_not_called()

    def test_no_chunks_means_no_generation(self):
        p = self._pipeline([])
        with patch.object(p, '_generate_answer') as generate, patch.object(p, '_verify_answer') as verify:
            result = p.run('What is DDL?', subject_id=1)
        generate.assert_not_called()
        verify.assert_not_called()
        self.assertEqual(result.final_answer, '')
        self.assertTrue(result.unverified_flag)


class LLMCallBudgetTest(TestCase):
    """A grounded standalone answer costs 2 LLM calls; a follow-up costs 3."""

    def _run(self, history, rewrite):
        chunk = RankedChunk(1, 'DML includes INSERT.', 0, 1, 'db.pdf', 0.8)
        replies = iter([
            '{"rewritten_query": "example of DML", "changes_made": ["resolved \'it\'"]}',
            'INSERT is a DML statement (Source: db.pdf).',
            '{"grounded": true, "supported_claims": ["INSERT is DML"], "unsupported_claims": [], "faithfulness_score": 1.0, "reasoning": "ok"}',
        ] if rewrite else [
            'INSERT is a DML statement (Source: db.pdf).',
            '{"grounded": true, "supported_claims": ["INSERT is DML"], "unsupported_claims": [], "faithfulness_score": 1.0, "reasoning": "ok"}',
        ])
        client = MagicMock()
        client.chat.completions.create.side_effect = lambda **kw: MagicMock(choices=[MagicMock(message=MagicMock(content=next(replies)))])
        p = ReasoningPipeline()
        p._retrieve_chunks = MagicMock(return_value=([chunk], 0.0, {}))
        with patch('reasoning.pipeline.OpenAI', return_value=client), \
                patch('reasoning.rewriter.OpenAI', return_value=client), \
                patch('reasoning.verifier.OpenAI', return_value=client):
            result = p.run('Give an example of it', subject_id=1, conversation_history=history, rewrite=rewrite)
        return result, client.chat.completions.create.call_count

    def test_standalone_answer_uses_two_calls(self):
        result, calls = self._run(None, rewrite=False)
        self.assertEqual(calls, 2)
        self.assertFalse(result.unverified_flag)

    def test_follow_up_answer_uses_three_calls(self):
        result, calls = self._run([{'role': 'user', 'content': 'What is DML?'}], rewrite=True)
        self.assertEqual(calls, 3)
        self.assertEqual(result.rewritten_query, 'example of DML')


from reasoning.models import AnswerEvaluation
from reasoning.pipeline import ReasoningResult
from reasoning.verifier import VerificationResult
from retrieval.reranking import RankedChunk


class HeuristicEvaluationTest(TestCase):
    def result(self, chunks, verification):
        return ReasoningResult(
            original_query='q', subject_id=1, pipeline_name='default',
            retrieved_chunks=chunks, final_answer='a', verification_result=verification,
        )

    def test_metrics_recorded_for_every_saved_session(self):
        chunks = [RankedChunk(1, 'x', 0, 1, 'a.pdf', 0.8), RankedChunk(2, 'y', 1, 1, 'a.pdf', 0.4)]
        verification = VerificationResult(grounded=False, supported_claims=['a', 'b', 'c'],
                                           unsupported_claims=['d'], faithfulness_score=0.75)
        session = ReasoningSession.create_from_result(self.result(chunks, verification))

        e = AnswerEvaluation.objects.get(session=session)
        self.assertEqual(e.evaluator, 'heuristic')
        self.assertEqual(e.faithfulness, 0.75)
        self.assertEqual(e.hallucination_rate, 0.25)
        self.assertAlmostEqual(e.retrieval_mean_similarity, 0.6)
        self.assertEqual(e.retrieval_top_similarity, 0.8)

    def test_no_context_answers_have_no_quality_scores(self):
        session = ReasoningSession.create_from_result(self.result([], None))
        e = AnswerEvaluation.objects.get(session=session)
        self.assertIsNone(e.faithfulness)
        self.assertIsNone(e.hallucination_rate)
        self.assertIsNone(e.retrieval_mean_similarity)


from io import StringIO
from django.core.management import call_command
from django.test import override_settings

from reasoning.evaluation import judge_session


class LLMJudgeTest(TestCase):
    def session(self, chunks=True):
        chunk_list = [RankedChunk(1, 'DDL is Data Definition Language.', 0, 1, 'db.pdf', 0.8)] if chunks else []
        return ReasoningSession.create_from_result(ReasoningResult(
            original_query='What is DDL?', subject_id=1, pipeline_name='default',
            retrieved_chunks=chunk_list, final_answer='DDL is Data Definition Language.',
        ))

    def test_judge_scores_are_parsed_clamped_and_stored(self):
        session = self.session()
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(
            content='{"answer_relevance": 1.4, "faithfulness": 0.9, "unsupported_claims": [], "reasoning": "Direct."}'))]

        e = judge_session(session, client=client)

        self.assertEqual((e.evaluator, e.answer_relevance, e.faithfulness), ('llm_judge', 1.0, 0.9))
        prompt = client.chat.completions.create.call_args.kwargs['messages'][0]['content']
        self.assertIn('DDL is Data Definition Language.', prompt)
        self.assertEqual(session.evaluations.count(), 2)  # heuristic + judge history

    @patch('reasoning.tasks.judge_answer.delay')
    def test_judge_only_queued_when_enabled_and_answer_had_materials(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            self.session()
        delay.assert_not_called()

        with override_settings(EVAL_LLM_JUDGE=True):
            with self.captureOnCommitCallbacks(execute=True):
                self.session(chunks=False)
            delay.assert_not_called()
            with self.captureOnCommitCallbacks(execute=True):
                session = self.session()
        delay.assert_called_once_with(session.pk)

    @patch('reasoning.management.commands.judge_answers.judge_session')
    def test_backlog_command_skips_already_judged(self, judge):
        judged, pending = self.session(), self.session()
        judged.evaluations.create(evaluator='llm_judge', answer_relevance=1.0)
        judge.return_value = MagicMock(answer_relevance=0.8, faithfulness=0.9)

        call_command('judge_answers', stdout=StringIO())

        judge.assert_called_once_with(pending)


class QualityDashboardTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('q', password='p')
        mine = Subject.objects.create(user=self.user, name='Mine')
        theirs = Subject.objects.create(user=User.objects.create_user('o', password='p'), name='Theirs')
        chunk = RankedChunk(1, 'x', 0, 1, 'a.pdf', 0.8)

        def save(subject, chunks, verification=None, unverified=False):
            r = ReasoningResult(original_query=f'q{subject.id}', subject_id=subject.id, pipeline_name='default',
                                retrieved_chunks=chunks, final_answer='a', verification_result=verification,
                                unverified_flag=unverified, latency_breakdown={'retrieval_ms': 10.0})
            return ReasoningSession.create_from_result(r)

        self.good = save(mine, [chunk], VerificationResult(True, ['a', 'b', 'c'], ['d'], 0.75))
        self.good.evaluations.create(evaluator='llm_judge', answer_relevance=0.3)
        self.empty = save(mine, [], unverified=True)
        save(theirs, [chunk], VerificationResult(True, ['a'], [], 1.0))

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_summary_covers_only_own_sessions(self):
        data = self.client.get(reverse('reasoning:quality')).json()

        totals = data['totals']
        self.assertEqual((totals['sessions'], totals['no_context']), (2, 1))
        self.assertEqual(totals['faithfulness'], 0.75)
        self.assertEqual(totals['hallucination_rate'], 0.25)
        self.assertEqual(totals['judge_relevance'], 0.3)
        self.assertEqual(data['retrieval']['no_context_rate'], 0.5)
        self.assertEqual(data['retrieval']['avg_retrieval_ms'], 10.0)
        self.assertEqual(len(data['trends']), 1)

        reasons = {f['session_id']: f['reasons'] for f in data['failures']}
        self.assertEqual(reasons[str(self.empty.session_id)], ['nothing retrieved'])
        self.assertEqual(reasons[str(self.good.session_id)], ['25% unsupported claims', 'low relevance (0.30)'])

    def test_bad_days_param(self):
        self.assertEqual(self.client.get(reverse('reasoning:quality'), {'days': 'x'}).status_code, 400)


from reasoning.pipeline import ReasoningError


class TraceCaptureTest(TestCase):
    def test_prompt_and_stage_timings_are_recorded(self):
        p = ReasoningPipeline()
        p._rewrite_query = lambda q, h: (RewriteResult('q', 'DDL meaning', [], 0, ''), 2.0)
        chunk = RankedChunk(1, 'DDL is Data Definition Language.', 0, 1, 'db.pdf', 0.8)
        p._retrieve_chunks = lambda q, s, n: ([chunk], 5.0, {'embedding_ms': 3.0, 'search_ms': 2.0})
        p._verify_answer = lambda a, c: (VerificationResult(True, ['x'], [], 1.0), 4.0)
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content='Data Definition Language.'))]
        p._openai_client = client

        result = p.run('What is DDL?', subject_id=1)

        user_prompt = result.prompts['generation'][1]['content']
        self.assertIn('DDL is Data Definition Language.', user_prompt)
        self.assertIn('QUESTION: What is DDL?', user_prompt)  # standalone: searched and asked as typed
        self.assertEqual(result.latency_breakdown['embedding_ms'], 3.0)
        self.assertEqual(result.to_dict()['prompts'], result.prompts)

    @patch('reasoning.pipeline.RetrievalPipeline')
    @patch('reasoning.pipeline.PipelineManager.get_pipeline', side_effect=ValueError('not configured'))
    def test_only_missing_pipeline_falls_back(self, get_pipeline, fallback_cls):
        fallback_cls.return_value.search.side_effect = ValueError('384 vs 768 dimensions')
        p = ReasoningPipeline()
        p._rewrite_query = lambda q, h: (RewriteResult('q', 'q', [], 0, ''), 0.0)

        with self.assertRaisesMessage(ReasoningError, 'dimensions'):
            p.run('What is DDL?', subject_id=1)
        fallback_cls.return_value.search.assert_called_once()


class InsightPagesTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('ip', password='p')
        subject = Subject.objects.create(user=self.user, name='DB')
        r = ReasoningResult(
            original_query='What is DDL?', subject_id=subject.id, pipeline_name='default',
            rewritten_query='DDL definition',
            retrieved_chunks=[RankedChunk(1, 'DDL is Data Definition Language.', 0, 1, 'db.pdf', 0.81)],
            generated_answer='DDL is Data Definition Language.', final_answer='DDL is Data Definition Language.',
            verification_result=VerificationResult(True, ['DDL is Data Definition Language'], ['It was invented in 1970'], 0.5),
            total_latency_ms=100.0,
            latency_breakdown={'classification_ms': 10.0, 'retrieval_ms': 30.0, 'embedding_ms': 20.0, 'search_ms': 10.0, 'generation_ms': 60.0},
            prompts={'generation': [{'role': 'system', 'content': 'SYSTEM-PROMPT-TEXT'}, {'role': 'user', 'content': 'USER-PROMPT-TEXT'}]},
        )
        self.session = ReasoningSession.create_from_result(r)
        self.client.force_login(self.user)

    def test_dashboard_lists_answers_and_failures(self):
        html = self.client.get(reverse('insights:dashboard')).content.decode()
        self.assertIn('What is DDL?', html)
        self.assertIn('50% unsupported claims', html)
        self.assertIn(reverse('insights:session', args=[self.session.session_id]), html)

    def test_debug_page_shows_every_stage(self):
        html = self.client.get(reverse('insights:session', args=[self.session.session_id])).content.decode()
        for expected in ['DDL definition', 'db.pdf', '0.810', 'USER-PROMPT-TEXT', 'It was invented in 1970', 'embedding', '60 ms']:
            self.assertIn(expected, html)

    def test_other_users_and_anonymous_are_blocked(self):
        self.client.force_login(get_user_model().objects.create_user('x', password='p'))
        self.assertEqual(self.client.get(reverse('insights:session', args=[self.session.session_id])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('insights:dashboard')).status_code, 302)


class StreamingPipelineTest(TestCase):
    def test_first_answer_streams_token_by_token(self):
        chunk = RankedChunk(1, 'DML includes INSERT.', 0, 1, 'db.pdf', 0.8)
        pieces = ['INSERT ', 'is ', 'DML.']
        client = MagicMock()
        client.chat.completions.create.return_value = iter(
            [MagicMock(choices=[MagicMock(delta=MagicMock(content=t))]) for t in pieces]
            + [MagicMock(choices=[MagicMock(delta=MagicMock(content=None))])]  # final chunk carries no text
        )
        p = ReasoningPipeline()
        p._openai_client = client
        p._retrieve_chunks = MagicMock(return_value=([chunk], 0.0, {}))
        p._verify_answer = MagicMock(return_value=(VerificationResult(True, ['x'], [], 1.0), 0.0))

        events = list(p.run_events('What is INSERT?', subject_id=1, stream=True))

        self.assertEqual([v for k, v in events if k == 'token'], pieces)
        self.assertEqual(events[-1][0], 'result')
        self.assertEqual(events[-1][1].final_answer, 'INSERT is DML.')
        self.assertTrue(client.chat.completions.create.call_args.kwargs['stream'])


class ReasoningQueryRateLimitTest(TestCase):
    @patch.dict('rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES', {'llm': '1/min'})
    def test_query_endpoint_is_capped(self):
        from django.core.cache import cache
        cache.clear()
        user = get_user_model().objects.create_user('rq', password='p')
        client = APIClient()
        client.force_authenticate(user)
        url = reverse('reasoning:query')
        client.post(url, {'query': 'hi', 'subject_id': 999}, format='json')  # 404, but counts as an LLM request
        self.assertEqual(client.post(url, {'query': 'hi', 'subject_id': 999}, format='json').status_code, 429)
