from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from subjects.models import (ChatMessage, ChatSession, Flashcard, Quiz, Subject, SubjectMaterial,
                             UserQuizAttempt)
from subjects.services.recommendations import recommend


class RecommendationTest(TestCase):
    def setUp(self):
        patcher = patch('subjects.tasks.build_material_sections.delay')  # no broker in tests; files without sections queue a build
        patcher.start()
        self.addCleanup(patcher.stop)
        self.user = get_user_model().objects.create_user('rec', password='p')
        self.db = Subject.objects.create(user=self.user, name='Databases')
        self.material = SubjectMaterial.objects.create(subject=self.db, file='subject_materials/sql.pdf', file_type='PDF', status='COMPLETED')

    def kinds(self):
        return [r['kind'] for r in recommend(self.user, limit=20)]

    def test_each_signal_produces_a_suggestion(self):
        Flashcard.objects.create(subject=self.db, question='q', answer='a')
        weak = Quiz.objects.create(subject=self.db, material=self.material, title='Weak')
        UserQuizAttempt.objects.create(user=self.user, quiz=weak, is_completed=True, score=40, end_time=timezone.now())
        Quiz.objects.create(subject=self.db, material=self.material, title='Untried')
        session = ChatSession.objects.create(user=self.user, subject=self.db)
        ChatMessage.objects.create(session=session, role='user', content='What is a B-tree index?')
        ChatMessage.objects.create(session=session, role='assistant', content="couldn't find",
                                   metadata={'model_info': {'pipeline': 'fallback'}})
        Subject.objects.create(user=self.user, name='Empty')

        recs = recommend(self.user, limit=20)
        # due cards aren't a suggestion: Home's review card covers them
        self.assertEqual([r['kind'] for r in recs], ['weak_quiz', 'knowledge_gap', 'untried_quiz', 'empty_subject'])  # no sections yet: no gaps
        by_kind = {r['kind']: r for r in recs}
        self.assertIn('40%', by_kind['weak_quiz']['reason'])
        self.assertIn('B-tree', by_kind['knowledge_gap']['reason'])
        self.assertIn('XP found nothing in your files for 1 recent question', by_kind['knowledge_gap']['reason'])

    def test_coverage_gaps_put_fading_then_untouched_then_shaky_first(self):
        from datetime import timedelta
        from subjects.models import FlashcardReview, Section
        old = timezone.now() - timedelta(days=30)
        fading, untouched, shaky = (Section.objects.create(material=self.material, order=i, title=t, kind='heading', first_chunk=i * 2, last_chunk=i * 2 + 1)
                                    for i, t in enumerate(['Joins', 'Indexes', 'Transactions']))
        for section, grade, reps, when in ((fading, 4, 2, old), (shaky, 3, 1, timezone.now())):
            card = Flashcard.objects.create(subject=self.db, material=self.material, section=section, question='q', answer='a')
            FlashcardReview.objects.create(user=self.user, flashcard=card, last_grade=grade, repetitions=reps, last_reviewed_at=when,
                                           due_at=timezone.now() + timedelta(days=5))
        recs = [r for r in recommend(self.user, limit=20) if r['kind'] == 'coverage_gap']
        self.assertEqual([(r['status'], r['section_id']) for r in recs], [('fading', fading.id), ('not_studied', untouched.id), ('shaky', shaky.id)])
        self.assertEqual(recs[0]['title'], 'Refresh Joins')
        self.assertIn('since', recs[0]['reason'])
        self.assertEqual(recs[1]['title'], 'Start Indexes')
        self.assertEqual(recs[2]['reason'], 'You rated one card Hard.')
        self.assertEqual(recommend(self.user, limit=20)[0]['section_id'], fading.id)  # gaps outrank everything else

    def test_good_scores_and_answered_questions_are_quiet(self):
        quiz = Quiz.objects.create(subject=self.db, material=self.material, title='Good')
        UserQuizAttempt.objects.create(user=self.user, quiz=quiz, is_completed=True, score=90, end_time=timezone.now())
        session = ChatSession.objects.create(user=self.user, subject=self.db)
        ChatMessage.objects.create(session=session, role='assistant', content='answer',
                                   metadata={'model_info': {'pipeline': 'reasoning'}})
        self.assertEqual(self.kinds(), [])

    def test_other_users_data_is_ignored(self):
        from subjects.models import Section
        other = get_user_model().objects.create_user('x', password='p')
        theirs = Subject.objects.create(user=other, name='Theirs')
        Flashcard.objects.create(subject=theirs, question='q', answer='a')
        their_file = SubjectMaterial.objects.create(subject=theirs, file='subject_materials/t.pdf', file_type='PDF', status='COMPLETED')
        Section.objects.create(material=their_file, order=0, title='Secret', kind='whole', first_chunk=0, last_chunk=0)
        self.assertEqual(self.kinds(), [])

    def test_home_api_shows_suggestions(self):
        Subject.objects.create(user=self.user, name='Maths')
        self.client.force_login(self.user)
        suggestions = self.client.get('/api/home/').json()['suggestions']
        self.assertEqual([s['title'] for s in suggestions], ['Upload your first file to Maths'])
        self.assertIsNone(suggestions[0]['section_id'])
