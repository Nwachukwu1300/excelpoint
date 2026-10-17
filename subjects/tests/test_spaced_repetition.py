from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from subjects.models import Flashcard, FlashcardReview, Subject
from subjects.services.spaced_repetition import due_cards, record_review


class SM2Test(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('sr', password='p')
        self.subject = Subject.objects.create(user=self.user, name='S')
        self.card = Flashcard.objects.create(subject=self.subject, question='DDL?', answer='Data Definition Language')

    def test_intervals_grow_on_recall_and_reset_on_lapse(self):
        r = record_review(self.user, self.card, 4)
        self.assertEqual((r.repetitions, r.interval_days), (1, 1))
        r = record_review(self.user, self.card, 4)
        self.assertEqual((r.repetitions, r.interval_days), (2, 6))
        r = record_review(self.user, self.card, 5)
        self.assertEqual(r.interval_days, 15)  # 6 days x ease 2.5 (the ease before this grade updates it)
        self.assertAlmostEqual(r.ease, 2.6)  # an "easy" grade raises ease for next time
        r = record_review(self.user, self.card, 1)
        self.assertEqual((r.repetitions, r.interval_days), (0, 1))
        self.assertAlmostEqual(r.due_at - timezone.now(), timedelta(days=1), delta=timedelta(seconds=5))

    def test_ease_never_drops_below_floor(self):
        for _ in range(10):
            r = record_review(self.user, self.card, 0)
        self.assertEqual(r.ease, 1.3)

    def test_invalid_grade(self):
        with self.assertRaises(ValueError):
            FlashcardReview(user=self.user, flashcard=self.card).apply_grade(6)

    def test_due_queue(self):
        other_user = get_user_model().objects.create_user('o', password='p')
        Flashcard.objects.create(subject=Subject.objects.create(user=other_user, name='X'), question='q', answer='a')

        self.assertEqual(list(due_cards(self.user)), [self.card])  # new card, and not other users' cards
        record_review(self.user, self.card, 4)
        self.assertEqual(list(due_cards(self.user)), [])
        FlashcardReview.objects.update(due_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(list(due_cards(self.user, self.subject)), [self.card])


class ReviewPageTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('rp', password='p')
        self.subject = Subject.objects.create(user=self.user, name='S')
        self.card = Flashcard.objects.create(subject=self.subject, question='What is DDL?', answer='Data Definition Language')
        self.client.force_login(self.user)
        self.url = reverse('review_flashcards', args=[self.subject.id])

    def test_shows_due_card_and_records_grade(self):
        self.assertContains(self.client.get(self.url), 'What is DDL?')
        response = self.client.post(self.url, {'flashcard_id': self.card.id, 'grade': 4})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(FlashcardReview.objects.get().last_grade, 4)
        self.assertContains(self.client.get(self.url), 'Nothing due')

    def test_rejects_bad_grade_and_other_users_subjects(self):
        self.assertEqual(self.client.post(self.url, {'flashcard_id': self.card.id, 'grade': 9}).status_code, 400)
        other = Subject.objects.create(user=get_user_model().objects.create_user('z', password='p'), name='Z')
        self.assertEqual(self.client.get(reverse('review_flashcards', args=[other.id])).status_code, 404)

    def test_subject_page_shows_due_count(self):
        self.assertContains(self.client.get(reverse('subject_detail', args=[self.subject.id])), '1 due')


class ReviewReminderTest(TestCase):
    def test_one_reminder_per_day_pointing_at_busiest_subject(self):
        from subjects.tasks import send_review_reminders
        from users.models import Notification

        user = get_user_model().objects.create_user('rr', password='p')
        light, heavy = Subject.objects.create(user=user, name='A'), Subject.objects.create(user=user, name='B')
        Flashcard.objects.create(subject=light, question='q', answer='a')
        for i in range(2):
            Flashcard.objects.create(subject=heavy, question=f'q{i}', answer='a')
        idle = get_user_model().objects.create_user('idle', password='p')
        done = Flashcard.objects.create(subject=Subject.objects.create(user=idle, name='C'), question='q', answer='a')
        record_review(idle, done, 5)  # nothing due for this user

        self.assertEqual(send_review_reminders(), {'reminders_sent': 1})
        note = Notification.objects.get()
        self.assertEqual((note.user, note.title, note.url), (user, '3 flashcards due for review', f'/subjects/{heavy.id}/review/'))
        self.assertEqual(send_review_reminders(), {'reminders_sent': 0})  # already reminded today

    def test_beat_schedule_points_at_real_task(self):
        from django.conf import settings
        from config.celery import app
        task = settings.CELERY_BEAT_SCHEDULE['flashcard-review-reminders']['task']
        app.loader.import_default_modules()
        self.assertIn(task, app.tasks)
