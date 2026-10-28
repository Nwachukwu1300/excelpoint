from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from subjects.models import Flashcard, FlashcardReview, Subject, SubjectMaterial

User = get_user_model()


class ReviewApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s', password='p')
        self.db = Subject.objects.create(user=self.user, name='Databases')
        self.maths = Subject.objects.create(user=self.user, name='Maths')
        notes = SubjectMaterial.objects.create(subject=self.db, file='subject_materials/notes.pdf', file_type='PDF')
        self.new = Flashcard.objects.create(subject=self.db, material=notes, question='What is a B-tree?', answer='A balanced tree')
        self.seen = Flashcard.objects.create(subject=self.db, question='ACID?', answer='Atomicity…')
        FlashcardReview.objects.create(user=self.user, flashcard=self.seen, repetitions=2, interval_days=6, ease=2.5,
                                       due_at=timezone.now() - timedelta(hours=1))
        later = Flashcard.objects.create(subject=self.db, question='Not yet', answer='x')
        FlashcardReview.objects.create(user=self.user, flashcard=later, due_at=timezone.now() + timedelta(days=2))
        self.maths_card = Flashcard.objects.create(subject=self.maths, question='2+2', answer='4')
        other = User.objects.create_user('o', password='p')
        self.theirs = Flashcard.objects.create(subject=Subject.objects.create(user=other, name='X'), question='secret', answer='x')
        self.client.force_login(self.user)

    def test_queue_lists_due_cards_with_honest_previews(self):
        data = self.client.get('/api/review/queue/').json()
        self.assertEqual(data['due_count'], 3)  # 'Not yet' and the other user's card are left out
        cards = {c['question']: c for c in data['cards']}
        self.assertEqual(set(cards), {'What is a B-tree?', 'ACID?', '2+2'})
        self.assertEqual(data['cards'][0]['question'], 'ACID?')  # overdue first, then new
        self.assertEqual(cards['What is a B-tree?']['material_name'], 'notes.pdf')
        self.assertEqual(cards['What is a B-tree?']['next_days'], {'1': 1, '3': 1, '4': 3, '5': 7})  # first-review gaps
        self.assertEqual(cards['ACID?']['next_days'], {'1': 1, '3': 15, '4': 15, '5': 15})  # 6 × ease 2.5 for a pass
        self.assertEqual([g['label'] for g in data['grades']], ['Again', 'Hard', 'Good', 'Easy'])

    def test_queue_for_one_subject(self):
        data = self.client.get(f'/api/review/queue/?subject={self.maths.id}').json()
        self.assertEqual([c['question'] for c in data['cards']], ['2+2'])
        self.assertEqual(data['subject'], {'id': self.maths.id, 'name': 'Maths'})
        self.assertEqual(self.client.get(f'/api/review/queue/?subject={self.theirs.subject_id}').status_code, 404)
        self.assertEqual(self.client.get('/api/review/queue/?subject=abc').status_code, 400)

    def test_previews_do_not_change_anything(self):
        before = FlashcardReview.objects.get(flashcard=self.seen)
        self.client.get('/api/review/queue/')
        after = FlashcardReview.objects.get(flashcard=self.seen)
        self.assertEqual((after.repetitions, after.interval_days, after.due_at), (before.repetitions, before.interval_days, before.due_at))
        self.assertFalse(FlashcardReview.objects.filter(flashcard=self.new).exists())

    def test_grade_schedules_the_card(self):
        r = self.client.post('/api/review/grade/', {'flashcard_id': self.seen.id, 'grade': 4}, content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['interval_days'], 15)
        review = FlashcardReview.objects.get(flashcard=self.seen)
        self.assertEqual((review.repetitions, review.last_grade), (3, 4))
        ids = [c['id'] for c in self.client.get('/api/review/queue/').json()['cards']]
        self.assertNotIn(self.seen.id, ids)

    def test_grade_rejects_bad_input_and_other_peoples_cards(self):
        post = lambda body: self.client.post('/api/review/grade/', body, content_type='application/json')
        self.assertEqual(post({'flashcard_id': self.new.id, 'grade': 2}).status_code, 400)  # not one of the buttons
        self.assertEqual(post({'flashcard_id': self.new.id}).status_code, 400)
        self.assertEqual(post({'flashcard_id': self.theirs.id, 'grade': 4}).status_code, 404)
        self.assertFalse(FlashcardReview.objects.filter(flashcard=self.theirs).exists())

    def test_anonymous_and_csrf(self):
        self.client.logout()
        self.assertEqual(self.client.get('/api/review/queue/').status_code, 403)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        r = client.post('/api/review/grade/', {'flashcard_id': self.new.id, 'grade': 4}, content_type='application/json')
        self.assertEqual(r.status_code, 403)
