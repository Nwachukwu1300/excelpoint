import io
import json
import zipfile
from datetime import timedelta
from unittest.mock import patch

import numpy as np
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from explain.models import ExplainSession, ExplainTurn
from subjects.models import (ContentChunk, Flashcard, FlashcardReview, Question, Quiz, Section, Subject, SubjectMaterial,
                             UserAnswer, UserQuizAttempt)
from subjects.services.coverage import subject_coverage
from subjects.tests import vec

User = get_user_model()
NOW = timezone.now()


class CoverageFixture(TestCase):
    def setUp(self):
        patcher = patch('subjects.tasks.build_material_sections.delay')  # no broker in tests
        self.queue = patcher.start()
        self.addCleanup(patcher.stop)
        self.user = User.objects.create_user('cov', password='p')
        self.client.force_login(self.user)
        self.subject = Subject.objects.create(user=self.user, name='Biology')
        self.file = SubjectMaterial.objects.create(subject=self.subject, file='', file_type='PDF', status='COMPLETED',
                                                   original_name='photo.pdf')
        for i in range(10):
            ContentChunk.objects.create(material=self.file, content=f'Passage {i} about {"light" if i < 4 else "dark"}.',
                                        chunk_index=i, embedding_vector=vec(1, 0) if i < 4 else vec(0, 1))
        # Light reactions is 4 passages, Calvin cycle 6
        self.light = Section.objects.create(material=self.file, order=0, title='Light reactions', kind='heading', first_chunk=0, last_chunk=3)
        self.calvin = Section.objects.create(material=self.file, order=1, title='Calvin cycle', kind='heading', first_chunk=4, last_chunk=9)
        self.quiz = Quiz.objects.create(subject=self.subject, material=self.file, title='Quiz on photo.pdf')

    def status(self, section):
        data = subject_coverage(self.user, self.subject)
        return next((s['status'], s['reason']) for f in data['files'] for s in f['sections'] if s['id'] == section.id)

    def card(self, section, grade, reps, days_ago=0, due_in=5):
        card = Flashcard.objects.create(subject=self.subject, material=self.file, section=section, question='q', answer='a')
        FlashcardReview.objects.create(user=self.user, flashcard=card, last_grade=grade, repetitions=reps,
                                       last_reviewed_at=NOW - timedelta(days=days_ago), due_at=NOW + timedelta(days=due_in))
        return card

    def answers(self, section, *results):
        attempt = UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, is_completed=True, score=50, end_time=NOW)
        for correct in results:
            q = Question.objects.create(quiz=self.quiz, section=section, text='q', question_type='short_answer',
                                        order=Question.objects.filter(quiz=self.quiz).count())
            UserAnswer.objects.create(attempt=attempt, question=q, answer_text='a', is_correct=correct)

    def explain(self, verdicts, chunk_index=0, days_ago=0):
        session = ExplainSession.objects.create(user=self.user, subject=self.subject, topic='Light')
        chunk = ContentChunk.objects.get(material=self.file, chunk_index=chunk_index)
        turn = ExplainTurn.objects.create(session=session, student_text='x', reply='y', marks=[
            {'sentence': 's', 'verdict': v, 'passage': {'chunk_id': chunk.id}} for v in verdicts])
        ExplainTurn.objects.filter(id=turn.id).update(created_at=NOW - timedelta(days=days_ago))


class StatusRulesTest(CoverageFixture):
    def test_nothing_done_is_not_studied_and_says_how_to_start(self):
        status, reason = self.status(self.light)
        self.assertEqual(status, 'not_studied')
        self.assertIn('take a quiz on it or explain it to XP', reason)  # no cards or questions of its own

    def test_right_once_is_shaky(self):
        self.answers(self.light, True)
        self.assertEqual(self.status(self.light), ('shaky', 'You got this right once. Practise it again to make it solid.'))

    def test_misses_and_hard_cards_are_explained_in_plain_words(self):
        self.answers(self.light, False, False, True)
        self.card(self.light, grade=3, reps=1)
        self.assertEqual(self.status(self.light), ('shaky', 'You missed 2 of 3 quiz questions on this and you rated one card Hard.'))

    def test_right_on_two_occasions_is_solid(self):
        self.card(self.light, grade=4, reps=2)
        status, reason = self.status(self.light)
        self.assertEqual(status, 'solid')
        self.assertIn('2 separate occasions', reason)

    def test_one_correct_explanation_is_enough_for_solid(self):
        self.explain(['correct', 'correct'])
        status, reason = self.status(self.light)
        self.assertEqual(status, 'solid')
        self.assertIn('including a correct explanation', reason)

    def test_a_wrong_explanation_beats_good_flashcards(self):
        self.card(self.light, grade=5, reps=4)
        self.explain(['correct', 'wrong'])
        self.assertEqual(self.status(self.light), ('shaky', 'Your last explanation of this had a mistake.'))
        self.explain(['correct'])  # a later, correct explanation clears it
        self.assertEqual(self.status(self.light)[0], 'solid')

    def test_not_in_notes_marks_and_other_sections_dont_count(self):
        self.explain(['not_in_notes'])
        self.explain(['correct'], chunk_index=5)  # the Calvin cycle
        self.assertEqual(self.status(self.light)[0], 'not_studied')
        self.assertEqual(self.status(self.calvin)[0], 'solid')

    def test_solid_fades_after_three_weeks_or_with_an_overdue_card(self):
        self.card(self.light, grade=4, reps=2, days_ago=22)
        status, reason = self.status(self.light)
        self.assertEqual(status, 'fading')
        self.assertIn("haven’t practised it since", reason)
        self.card(self.calvin, grade=4, reps=2, due_in=-2)
        self.assertEqual(self.status(self.calvin), ('fading', 'One of its flashcards is overdue. Review them before you forget.'))

    def test_fresh_question_answers_count_for_their_section(self):
        UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, uses_dynamic_questions=True, is_completed=True, score=100,
                                       end_time=NOW, dynamic_questions=[{'id': 'd1', 'text': 'q', 'type': 'short_answer',
                                                                          'section_id': self.calvin.id, 'is_correct': True}])
        self.assertEqual(self.status(self.calvin)[0], 'shaky')  # right once
        self.assertEqual(self.status(self.light)[0], 'not_studied')

    def test_other_students_work_never_counts(self):
        other = User.objects.create_user('other', password='p')
        card = Flashcard.objects.create(subject=self.subject, material=self.file, section=self.light, question='q', answer='a')
        FlashcardReview.objects.create(user=other, flashcard=card, last_grade=5, repetitions=3, last_reviewed_at=NOW, due_at=NOW + timedelta(days=9))
        self.assertEqual(self.status(self.light)[0], 'not_studied')


class CoverageApiTest(CoverageFixture):
    def test_map_weights_by_size_and_names_the_biggest_gap(self):
        self.card(self.light, grade=4, reps=2)
        data = self.client.get(f'/api/subjects/{self.subject.id}/coverage/').json()
        self.assertEqual(data['percent'], 40)  # 4 of 10 passages
        self.assertEqual(data['sentence'], "Calvin cycle hasn’t come up yet.")
        self.assertEqual(data['counts'], {'not_studied': 1, 'shaky': 0, 'solid': 1, 'fading': 0})
        file = data['files'][0]
        self.assertEqual((file['name'], file['state'], file['percent'], file['studied']), ('photo.pdf', 'ready', 40, 1))
        self.assertEqual([(s['title'], s['status'], s['size']) for s in file['sections']], [('Light reactions', 'solid', 4), ('Calvin cycle', 'not_studied', 6)])
        self.assertNotIn('rows', data)
        self.assertNotIn('Passage', json.dumps(data))  # no passage text in the map: it stays small on slow 3G

    def test_new_processing_failed_and_deleted_files(self):
        SubjectMaterial.objects.create(subject=self.subject, file='', file_type='PDF', status='PROCESSING', original_name='new.pdf')
        SubjectMaterial.objects.create(subject=self.subject, file='', file_type='PDF', status='FAILED', original_name='bad.pdf', error='No text found.')
        old = SubjectMaterial.objects.create(subject=self.subject, file='', file_type='PDF', status='COMPLETED', original_name='old.pdf')
        files = {f['name']: f for f in self.client.get(f'/api/subjects/{self.subject.id}/coverage/').json()['files']}
        self.assertEqual({n: f['state'] for n, f in files.items()}, {'photo.pdf': 'ready', 'new.pdf': 'processing', 'bad.pdf': 'failed', 'old.pdf': 'building'})
        self.assertEqual(files['bad.pdf']['error'], 'No text found.')
        self.queue.assert_called_once_with(old.id)  # a file from before the map gets its sections in the background
        self.file.delete()
        names = [f['name'] for f in self.client.get(f'/api/subjects/{self.subject.id}/coverage/').json()['files']]
        self.assertNotIn('photo.pdf', names)
        self.assertFalse(Section.objects.filter(id=self.light.id).exists())

    def test_a_subject_with_no_files_is_empty(self):
        empty = Subject.objects.create(user=self.user, name='Maths')
        data = self.client.get(f'/api/subjects/{empty.id}/coverage/').json()
        self.assertEqual((data['state'], data['percent'], data['files']), ('empty', 0, []))

    def test_a_one_section_file_is_still_a_map(self):
        Section.objects.all().delete()
        Section.objects.create(material=self.file, order=0, title='Photosynthesis', kind='whole', first_chunk=0, last_chunk=9)
        data = self.client.get(f'/api/subjects/{self.subject.id}/coverage/').json()
        self.assertEqual(data['sentence'], 'Start with Photosynthesis.')
        self.assertEqual(len(data['files'][0]['sections']), 1)

    def test_section_detail_has_its_passages_and_reason(self):
        self.answers(self.light, False)
        data = self.client.get(f'/api/sections/{self.light.id}/').json()
        self.assertEqual((data['title'], data['status'], data['file']['name']), ('Light reactions', 'shaky', 'photo.pdf'))
        self.assertEqual(data['reason'], 'You missed 1 of 1 quiz questions on this.')
        self.assertEqual([p['chunk_index'] for p in data['passages']], [0, 1, 2, 3])
        self.assertTrue(data['text'].startswith('Passage 0 about light. Passage 1'))

    def test_overlapping_passages_are_joined_without_repeats(self):
        from subjects.coverage_api import joined
        self.assertEqual(joined(['. The cycle uses ATP to make', 'to make sugar in the stroma.']), 'The cycle uses ATP to make sugar in the stroma.')
        self.assertEqual(joined(['One.', 'Two.']), 'One. Two.')

    @patch('subjects.coverage_api.generate_dynamic_quiz_questions')
    def test_a_section_quiz_asks_five_fresh_questions_about_that_section(self, task):
        self.quiz.delete()  # a file whose quiz couldn't be made still gets one
        r = self.client.post(f'/api/sections/{self.calvin.id}/quiz/')
        self.assertEqual(r.status_code, 201)
        attempt = UserQuizAttempt.objects.get(id=r.json()['id'])
        self.assertEqual((attempt.section, attempt.uses_dynamic_questions, r.json()['quiz']['section']), (self.calvin, True, 'Calvin cycle'))
        task.delay.assert_called_once_with(attempt.id, num_questions=5)

    def test_section_quiz_generation_reads_only_that_section(self):
        from subjects.tasks import generate_dynamic_quiz_questions
        attempt = UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, uses_dynamic_questions=True, section=self.light)
        question = {'question': 'Where?', 'type': 'short_answer', 'correct_answers': ['thylakoid']}
        with patch('subjects.tasks._generate_dynamic_questions_with_openai', return_value=[question]) as write:
            generate_dynamic_quiz_questions(attempt.id, num_questions=5)
        text = write.call_args.args[0]
        self.assertIn('Passage 3 about light', text)
        self.assertNotIn('dark', text)
        attempt.refresh_from_db()
        self.assertEqual(attempt.dynamic_questions[0]['section_id'], self.light.id)

    def test_whole_file_fresh_questions_are_linked_to_their_nearest_section(self):
        from subjects.tasks import generate_dynamic_quiz_questions
        attempt = UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, uses_dynamic_questions=True)
        questions = [{'question': 'About dark?', 'type': 'short_answer', 'correct_answers': ['x']},
                     {'question': 'About light?', 'type': 'short_answer', 'correct_answers': ['y']}]
        model = patch('subjects.services.sections.load_embedding_model').start()
        self.addCleanup(patch.stopall)
        model.return_value.encode.side_effect = lambda texts: np.array([vec(0, 1) if 'dark' in t else vec(1, 0) for t in texts])
        with patch('subjects.tasks._generate_dynamic_questions_with_openai', return_value=questions):
            generate_dynamic_quiz_questions(attempt.id, num_questions=2)
        attempt.refresh_from_db()
        self.assertEqual([q['section_id'] for q in attempt.dynamic_questions], [self.calvin.id, self.light.id])

    def test_section_cards_are_all_offered_due_or_not(self):
        due_later = self.card(self.light, grade=4, reps=2, due_in=9)
        new = Flashcard.objects.create(subject=self.subject, material=self.file, section=self.light, question='new', answer='a')
        self.card(self.calvin, grade=4, reps=2)  # another section's card stays out
        data = self.client.get(f'/api/review/queue/?section={self.light.id}').json()
        self.assertEqual({c['id'] for c in data['cards']}, {due_later.id, new.id})
        self.assertEqual(data['section'], {'id': self.light.id, 'title': 'Light reactions'})
        self.assertEqual(self.client.get('/api/review/queue/?section=x').status_code, 400)

    @patch('explain.service._embed', side_effect=lambda t: np.array(vec(1, 0)))
    def test_explaining_a_section_uses_only_its_passages(self, _):
        r = self.client.post(f'/api/subjects/{self.subject.id}/explain/', {'section_id': self.calvin.id}, content_type='application/json')
        self.assertEqual(r.status_code, 201)
        session = ExplainSession.objects.get(id=r.json()['id'])
        self.assertEqual((session.topic, session.section), ('Calvin cycle', self.calvin))
        self.assertTrue(session.passages and all('dark' in p['content'] for p in session.passages))

    def test_other_students_cannot_see_or_use_sections(self):
        other = User.objects.create_user('nosy', password='p')
        self.client.force_login(other)
        self.assertEqual(self.client.get(f'/api/subjects/{self.subject.id}/coverage/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/sections/{self.light.id}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/sections/{self.light.id}/quiz/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/review/queue/?section={self.light.id}').status_code, 404)
        theirs = Subject.objects.create(user=other, name='Theirs')
        r = self.client.post(f'/api/subjects/{theirs.id}/explain/', {'section_id': self.light.id}, content_type='application/json')
        self.assertIn(r.status_code, (400, 409))  # never someone else's notes

    def test_the_data_download_has_each_files_sections(self):
        self.card(self.light, grade=4, reps=2)
        response = self.client.get('/api/me/export/')
        data = json.loads(zipfile.ZipFile(io.BytesIO(b''.join(response.streaming_content))).read('data.json'))
        subject = data['subjects'][0]
        self.assertEqual(subject['studied_percent'], 40)
        self.assertEqual([(s['name'], s['status']) for s in subject['files'][0]['coverage_sections']],
                         [('Light reactions', 'solid'), ('Calvin cycle', 'not studied')])
