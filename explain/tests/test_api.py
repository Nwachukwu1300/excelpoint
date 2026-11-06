import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

import numpy as np
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from explain.models import ExplainSession, ExplainTurn
from reasoning.models import ReasoningSession
from subjects.models import ContentChunk, Subject, SubjectMaterial
from subjects.tests import vec

User = get_user_model()
TREE = 'B-trees stay balanced: every leaf sits at the same depth, so a lookup reads about log n pages.'
HASH = 'A hash index maps each key to a bucket. It is fast for exact matches but cannot answer range queries.'


def fake_embed(texts):
    """Tree talk points one way, hash talk another, anything else a third: enough to test the search gate."""
    def one(text):
        text = text.lower()
        return np.array(vec(1, 0) if 'tree' in text else vec(0, 1) if 'hash' in text else vec(0, 0, 1))
    return np.array([one(t) for t in texts]) if isinstance(texts, list) else one(texts)


def llm_reply(data):
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(data)))])
    return client


CHECK = {
    'kind': 'explanation',
    'statements': [
        {'text': 'B-trees stay balanced.', 'verdict': 'correct', 'passage': 'P1', 'quote': 'B-trees stay balanced'},
        {'text': 'Leaves can be at any depth.', 'verdict': 'wrong', 'passage': 'P1', 'quote': 'not in there',
         'note': 'Every leaf sits at the same depth.'},
        {'text': 'They were invented in 1970.', 'verdict': 'not_in_notes', 'passage': None},
        {'text': 'Made-up evidence.', 'verdict': 'correct', 'passage': 'P9'},
    ],
    'key_points': [{'point': 'B-trees stay balanced', 'passage': 'P1'}, {'point': 'Lookups read about log n pages', 'passage': 'P1'}],
    'covered': ['K1'],
    'answer': '',
    'reply': 'You got the balance right. Leaves all sit at the same depth, though. How many pages does a lookup read?',
}


@patch('explain.service._embed', side_effect=fake_embed)
class ExplainApiTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('ex', password='p')
        self.client.force_login(self.user)
        self.subject = Subject.objects.create(user=self.user, name='Databases')
        self.material = SubjectMaterial.objects.create(
            subject=self.subject, file='subject_materials/indexes.pdf', original_name='indexes.pdf', file_type='PDF',
            status='COMPLETED', summary='Intro line.\n- **B-tree index** keeps keys sorted.\n- **Hash index** maps keys to buckets.\n'
                                        '- all leaves sit at the same depth.\n- **b-tree index** again.')
        ContentChunk.objects.create(material=self.material, content=TREE, chunk_index=0, embedding_vector=vec(1, 0))
        ContentChunk.objects.create(material=self.material, content=HASH, chunk_index=1, embedding_vector=vec(0, 1))

    def start(self, **body):
        return self.client.post(f'/api/subjects/{self.subject.id}/explain/', body, content_type='application/json')

    def turn(self, session_id, text='B-trees stay balanced. Leaves can be at any depth.', mode='text'):
        return self.client.post(f'/api/explain/{session_id}/turns/', {'text': text, 'mode': mode}, content_type='application/json')

    def test_lists_files_topics_from_summaries_and_sessions(self, _):
        ExplainSession.objects.create(user=self.user, subject=self.subject, topic='B-trees', coverage=0.5, accuracy=1)
        data = self.client.get(f'/api/subjects/{self.subject.id}/explain/').json()
        self.assertTrue(data['files_ready'])
        self.assertEqual(data['files'], [{'id': self.material.id, 'name': 'indexes.pdf'}])
        self.assertEqual(data['topics'], ['B-tree index', 'Hash index', 'All leaves sit at the same depth'])  # deduped, capitalised
        self.assertEqual([s['topic'] for s in data['sessions']], ['B-trees'])
        self.assertEqual(data['limit']['used'], 0)

    def test_a_covered_topic_starts_with_only_the_relevant_passages(self, _):
        r = self.start(topic='How B-trees work')
        self.assertEqual(r.status_code, 201)
        session = ExplainSession.objects.get(id=r.json()['id'])
        self.assertEqual([p['content'] for p in session.passages], [TREE])
        self.assertEqual(r.json()['voice'], 'browser')

    def test_a_topic_not_in_the_files_suggests_close_ones(self, _):
        r = self.start(topic='Photosynthesis')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['covered'])
        self.assertEqual(set(r.json()['suggestions']), {'B-tree index', 'Hash index', 'All leaves sit at the same depth'})
        self.assertFalse(ExplainSession.objects.exists())

    def test_a_file_starts_a_session_named_after_it(self, _):
        r = self.start(material_id=self.material.id)
        self.assertEqual(r.json()['topic'], 'indexes.pdf')

    def test_no_ready_files_is_409(self, _):
        self.material.status = 'PROCESSING'
        self.material.save()
        r = self.start(topic='B-trees')
        self.assertEqual(r.status_code, 409)
        self.assertIn('Upload notes', r.json()['detail'])

    def test_a_check_marks_statements_with_evidence_and_saves_a_trace(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        with patch('explain.service.OpenAI', return_value=llm_reply(CHECK)):
            data = self.turn(session_id).json()
        marks = data['turns'][0]['marks']
        self.assertEqual([m['verdict'] for m in marks], ['correct', 'wrong', 'not_in_notes', 'not_in_notes'])
        self.assertEqual(marks[0]['passage']['content'], TREE)
        self.assertEqual(marks[0]['quote'], 'B-trees stay balanced')
        self.assertEqual(marks[1]['quote'], '')  # a quote that isn't in the passage is dropped
        self.assertEqual(marks[1]['note'], 'Every leaf sits at the same depth.')
        self.assertIsNone(marks[3]['passage'])  # evidence XP can't show doesn't count as correct
        self.assertEqual([(k['id'], k['covered']) for k in data['key_points']], [('K1', True), ('K2', False)])
        self.assertFalse(data['finished'])
        self.assertEqual(data['limit']['used'], 1)
        trace = ReasoningSession.objects.get()
        self.assertEqual((trace.kind, trace.faithfulness_score, trace.chunks.count()), ('explain', 0.5, 1))
        self.assertEqual(str(trace.session_id), data['turns'][0]['trace_id'])

    def test_later_checks_keep_the_key_points_and_finish_after_the_last_round(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        with patch('explain.service.OpenAI', return_value=llm_reply(CHECK)):
            self.turn(session_id)
        later = dict(CHECK, statements=[CHECK['statements'][0]], key_points=[], covered=['K2'])
        with override_settings(EXPLAIN_MAX_ROUNDS=2), patch('explain.service.OpenAI', return_value=llm_reply(later)) as openai:
            data = self.turn(session_id, 'A lookup reads log n pages.').json()
        prompt = openai.return_value.chat.completions.create.call_args.kwargs['messages'][1]['content']
        self.assertIn('K1: B-trees stay balanced (already covered)', prompt)
        self.assertIn('This is the last round', prompt)
        self.assertTrue(data['finished'])
        self.assertEqual(data['coverage'], 1.0)
        self.assertAlmostEqual(data['accuracy'], 2 / 3)  # two correct, one wrong
        self.assertEqual(len(data['summary']['nailed']), 2)
        self.assertEqual(data['summary']['wrong'][0]['note'], 'Every leaf sits at the same depth.')
        self.assertEqual(data['summary']['missed'], [])
        self.assertEqual(self.turn(session_id).status_code, 409)

    def test_questions_and_off_topic_messages_get_no_marks(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        question = dict(CHECK, kind='question', answer='Every leaf is at the same depth.', reply='Same depth. Carry on!')
        with patch('explain.service.OpenAI', return_value=llm_reply(question)):
            data = self.turn(session_id, 'Wait, are all the leaves at the same depth?').json()
        turn = data['turns'][0]
        self.assertEqual((turn['kind'], turn['marks'], turn['answer']), ('question', [], 'Every leaf is at the same depth.'))
        with patch('explain.service.OpenAI', return_value=llm_reply(dict(CHECK, kind='off_topic', answer='x'))):
            turn = self.turn(session_id, 'What should I eat tonight?').json()['turns'][1]
        self.assertEqual((turn['kind'], turn['marks'], turn['answer']), ('off_topic', [], ''))

    def test_a_long_reply_is_cut_for_speaking(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        long = dict(CHECK, reply='Good start. ' + 'word ' * 100)
        with patch('explain.service.OpenAI', return_value=llm_reply(long)):
            reply = self.turn(session_id).json()['turns'][0]['reply']
        self.assertLessEqual(len(reply.split()), 60)

    def test_a_failed_check_is_503_and_not_counted(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        broken = MagicMock()
        broken.chat.completions.create.side_effect = RuntimeError('down')
        with patch('explain.service.OpenAI', return_value=broken):
            r = self.turn(session_id)
        self.assertEqual(r.status_code, 503)
        self.assertFalse(ExplainTurn.objects.exists())

    @override_settings(EXPLAIN_DAILY_LIMIT=1)
    def test_the_daily_limit_says_when_they_can_go_again(self, _):
        session = ExplainSession.objects.create(user=self.user, subject=self.subject, topic='B-trees', passages=[])
        old = ExplainTurn.objects.create(session=session, student_text='x', reply='y')
        r = self.turn(session.id)
        self.assertEqual(r.status_code, 429)
        self.assertIn("today's 1 checks", r.json()['detail'])
        self.assertIsNotNone(r.json()['resets_at'])
        # a day later the check is free again
        ExplainTurn.objects.filter(id=old.id).update(created_at=timezone.now() - timedelta(hours=25))
        with patch('explain.service.OpenAI', return_value=llm_reply(CHECK)):
            self.assertEqual(self.turn(session.id).status_code, 200)

    def test_empty_or_long_text_is_rejected(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        self.assertEqual(self.turn(session_id, '  ').status_code, 400)
        self.assertEqual(self.turn(session_id, 'x' * 4001).status_code, 400)

    @override_settings(OPENAI_API_KEY='test')
    def test_transcribe_returns_text_and_rejects_unclear_or_long_audio(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        url = f'/api/explain/{session_id}/transcribe/'
        openai = MagicMock()
        openai.audio.transcriptions.create.return_value = MagicMock(text=' B-trees stay balanced always. ')
        with patch('explain.service.OpenAI', return_value=openai), override_settings(EXPLAIN_TRANSCRIBE_MODEL='cheap-model'):
            r = self.client.post(url, {'audio': SimpleUploadedFile('clip.webm', b'abc', 'audio/webm')})
        self.assertEqual(r.json(), {'text': 'B-trees stay balanced always.'})
        call = openai.audio.transcriptions.create.call_args.kwargs
        self.assertEqual((call['model'], call['file'][0]), ('cheap-model', 'clip.webm'))
        openai.audio.transcriptions.create.return_value = MagicMock(text='um')
        with patch('explain.service.OpenAI', return_value=openai):
            r = self.client.post(url, {'audio': SimpleUploadedFile('clip.webm', b'abc', 'audio/webm')})
        self.assertEqual(r.status_code, 422)
        self.assertIn("couldn't make out any words", r.json()['detail'])
        big = SimpleUploadedFile('clip.webm', b'x' * (5 * 1024 * 1024 + 1), 'audio/webm')
        self.assertEqual(self.client.post(url, {'audio': big}).status_code, 400)

    def test_speech_is_204_for_the_browser_voice_and_mp3_for_openai(self, _):
        session = ExplainSession.objects.create(user=self.user, subject=self.subject, topic='B-trees')
        turn = ExplainTurn.objects.create(session=session, student_text='x', reply='Nice work.')
        self.assertEqual(self.client.get(f'/api/explain/turns/{turn.id}/speech/').status_code, 204)
        openai = MagicMock()
        openai.audio.speech.create.return_value = MagicMock(content=b'mp3')
        with override_settings(XP_VOICE='openai'), patch('explain.voice.OpenAI', return_value=openai):
            r = self.client.get(f'/api/explain/turns/{turn.id}/speech/')
        self.assertEqual((r['Content-Type'], r.content), ('audio/mpeg', b'mp3'))
        self.assertEqual(openai.audio.speech.create.call_args.kwargs['input'], 'Nice work.')

    def test_finish_early_scores_what_was_said(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        with patch('explain.service.OpenAI', return_value=llm_reply(CHECK)):
            self.turn(session_id)
        data = self.client.post(f'/api/explain/{session_id}/finish/').json()
        self.assertEqual((data['finished'], data['coverage'], data['accuracy']), (True, 0.5, 0.5))
        self.assertEqual([k['point'] for k in data['summary']['missed']], ['Lookups read about log n pages'])
        self.assertEqual(len(data['summary']['not_in_notes']), 2)

    def test_delete_removes_the_session_and_its_traces(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        with patch('explain.service.OpenAI', return_value=llm_reply(CHECK)):
            self.turn(session_id)
        self.assertEqual(self.client.delete(f'/api/explain/{session_id}/').status_code, 204)
        self.assertFalse(ExplainSession.objects.exists())
        self.assertFalse(ExplainTurn.objects.exists())
        self.assertFalse(ReasoningSession.objects.exists())

    def test_other_students_sessions_and_subjects_are_404(self, _):
        other = User.objects.create_user('other', password='p')
        theirs = Subject.objects.create(user=other, name='Theirs')
        session = ExplainSession.objects.create(user=other, subject=theirs, topic='Secret')
        turn = ExplainTurn.objects.create(session=session, student_text='x', reply='y')
        self.assertEqual(self.client.get(f'/api/subjects/{theirs.id}/explain/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/explain/{session.id}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/explain/{session.id}/').status_code, 404)
        self.assertEqual(self.turn(session.id).status_code, 404)
        self.assertEqual(self.client.get(f'/api/explain/turns/{turn.id}/speech/').status_code, 404)
        self.assertTrue(ExplainSession.objects.filter(id=session.id).exists())


@patch('explain.service._embed', side_effect=fake_embed)
class ExplainInsightsTest(TestCase):
    """Checks show up in Insights with a trace, but stay out of the answer-quality numbers."""

    setUp = ExplainApiTest.setUp
    start = ExplainApiTest.start
    turn = ExplainApiTest.turn

    def test_checks_are_listed_and_traced_but_not_scored(self, _):
        session_id = self.start(topic='B-trees').json()['id']
        with patch('explain.service.OpenAI', return_value=llm_reply(CHECK)):
            self.turn(session_id)
        data = self.client.get('/api/reasoning/insights/').json()
        self.assertEqual(data['summary']['totals']['sessions'], 0)
        self.assertEqual((data['recent'][0]['kind'], data['recent'][0]['category']), ('explain', 'Explain it back'))
        trace = self.client.get(f"/api/reasoning/sessions/{data['recent'][0]['session_id']}/trace/").json()
        self.assertEqual(trace['explain']['marks'][0]['verdict'], 'correct')
        self.assertEqual(trace['explain_session'], {'id': session_id, 'subject_id': self.subject.id})
        self.assertEqual([s['name'] for s in trace['stages']], ['search', 'verification'])
        self.assertIn('B-trees stay balanced. Leaves can be at any depth.', trace['prompts']['check'][1]['content'])
