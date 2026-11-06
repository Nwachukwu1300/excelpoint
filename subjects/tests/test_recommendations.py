from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from subjects.models import (ChatMessage, ChatSession, Flashcard, Quiz, Subject, SubjectMaterial,
                             UserQuizAttempt)
from subjects.services.recommendations import recommend


class RecommendationTest(TestCase):
    def setUp(self):
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
        self.assertEqual([r['kind'] for r in recs], ['weak_quiz', 'knowledge_gap', 'untried_quiz', 'explain_back', 'empty_subject'])
        by_kind = {r['kind']: r for r in recs}
        self.assertIn('40%', by_kind['weak_quiz']['reason'])
        self.assertIn('B-tree', by_kind['knowledge_gap']['reason'])
        self.assertIn('XP found nothing in your files for 1 recent question', by_kind['knowledge_gap']['reason'])
        self.assertEqual((by_kind['explain_back']['title'], by_kind['explain_back']['material_id']),
                         ('Explain sql.pdf back to XP', self.material.id))

    def test_explain_back_suggests_the_newest_file_not_explained_yet(self):
        from explain.models import ExplainSession
        newer = SubjectMaterial.objects.create(subject=self.db, file='subject_materials/joins.pdf', file_type='PDF', status='COMPLETED')
        SubjectMaterial.objects.create(subject=self.db, file='subject_materials/draft.pdf', file_type='PDF', status='PROCESSING')
        ExplainSession.objects.create(user=self.user, subject=self.db, topic='typed topic')  # no file: hides nothing
        self.assertEqual(recommend(self.user)[0]['material_id'], newer.id)
        ExplainSession.objects.create(user=self.user, subject=self.db, material=newer, topic='joins.pdf')
        self.assertEqual(recommend(self.user)[0]['material_id'], self.material.id)

    def test_good_scores_and_answered_questions_are_quiet(self):
        from explain.models import ExplainSession
        ExplainSession.objects.create(user=self.user, subject=self.db, material=self.material, topic='sql.pdf')
        quiz = Quiz.objects.create(subject=self.db, material=self.material, title='Good')
        UserQuizAttempt.objects.create(user=self.user, quiz=quiz, is_completed=True, score=90, end_time=timezone.now())
        session = ChatSession.objects.create(user=self.user, subject=self.db)
        ChatMessage.objects.create(session=session, role='assistant', content='answer',
                                   metadata={'model_info': {'pipeline': 'reasoning'}})
        self.assertEqual(self.kinds(), [])

    def test_other_users_data_is_ignored(self):
        from explain.models import ExplainSession
        ExplainSession.objects.create(user=self.user, subject=self.db, material=self.material, topic='sql.pdf')
        other = get_user_model().objects.create_user('x', password='p')
        theirs = Subject.objects.create(user=other, name='Theirs')
        Flashcard.objects.create(subject=theirs, question='q', answer='a')
        SubjectMaterial.objects.create(subject=theirs, file='subject_materials/t.pdf', file_type='PDF', status='COMPLETED')
        self.assertEqual(self.kinds(), [])

    def test_home_api_shows_suggestions(self):
        Subject.objects.create(user=self.user, name='Maths')
        self.client.force_login(self.user)
        suggestions = self.client.get('/api/home/').json()['suggestions']
        self.assertEqual([s['title'] for s in suggestions], ['Explain sql.pdf back to XP', 'Upload your first file to Maths'])
        self.assertEqual((suggestions[0]['material_id'], suggestions[1]['material_id']), (self.material.id, None))
