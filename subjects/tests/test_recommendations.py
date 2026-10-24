from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
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
        # a 40% score outranks a single due card; priority grows with how far below 70% it is
        self.assertEqual([r['kind'] for r in recs], ['weak_quiz', 'review', 'knowledge_gap', 'untried_quiz', 'empty_subject'])
        by_kind = {r['kind']: r for r in recs}
        self.assertIn('40%', by_kind['weak_quiz']['reason'])
        self.assertIn('B-tree', by_kind['knowledge_gap']['reason'])
        self.assertIn('1 recent question wasn’t covered', by_kind['knowledge_gap']['reason'])
        self.assertEqual(by_kind['review']['url'], reverse('review_flashcards', args=[self.db.id]))

    def test_good_scores_and_answered_questions_are_quiet(self):
        quiz = Quiz.objects.create(subject=self.db, material=self.material, title='Good')
        UserQuizAttempt.objects.create(user=self.user, quiz=quiz, is_completed=True, score=90, end_time=timezone.now())
        session = ChatSession.objects.create(user=self.user, subject=self.db)
        ChatMessage.objects.create(session=session, role='assistant', content='answer',
                                   metadata={'model_info': {'pipeline': 'reasoning'}})
        self.assertEqual(self.kinds(), [])

    def test_other_users_data_is_ignored(self):
        other = get_user_model().objects.create_user('x', password='p')
        Flashcard.objects.create(subject=Subject.objects.create(user=other, name='Theirs'), question='q', answer='a')
        self.assertEqual(self.kinds(), [])

    def test_dashboard_shows_suggestions(self):
        Flashcard.objects.create(subject=self.db, question='q', answer='a')
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('learning:dashboard')), 'Review 1 flashcard in Databases')

    def test_due_cards_are_counted_per_subject_not_per_card(self):
        from subjects.services.spaced_repetition import record_review
        from django.utils import timezone as tz
        from subjects.models import FlashcardReview
        cards = [Flashcard.objects.create(subject=self.db, question=f'q{i}', answer='a') for i in range(3)]
        record_review(self.user, cards[0], 4)
        FlashcardReview.objects.update(due_at=tz.now() - tz.timedelta(hours=1))  # one overdue, two new
        reviews = [r for r in recommend(self.user) if r['kind'] == 'review']
        self.assertEqual([r['title'] for r in reviews], ['Review 3 flashcards in Databases'])
