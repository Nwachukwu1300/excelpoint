from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile
from django.test import TestCase
from django.utils import timezone

from subjects.models import Flashcard, FlashcardReview, Quiz, Subject, SubjectMaterial, UserQuizAttempt

User = get_user_model()


class WorkspaceApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s', password='p')
        self.other = User.objects.create_user('o', password='p')
        self.db = Subject.objects.create(user=self.user, name='Database Systems')
        self.theirs = Subject.objects.create(user=self.other, name='Secret')
        now = timezone.now()
        self.old = SubjectMaterial.objects.create(subject=self.db, file='subject_materials/old.pdf', file_type='PDF', status='COMPLETED', summary='- B-trees stay balanced')
        self.new = SubjectMaterial.objects.create(subject=self.db, file='subject_materials/new.docx', file_type='DOCX', status='PROCESSING')
        SubjectMaterial.objects.filter(pk=self.old.pk).update(created_at=now - timedelta(days=3))
        self.quiz = Quiz.objects.create(subject=self.db, material=self.old, title='Old quiz')
        self.client.force_login(self.user)

    def test_create_subject_rejects_duplicates_ignoring_case(self):
        r = self.client.post('/api/subjects/', {'name': '  database systems '}, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {'name': ['A subject named database systems already exists.']})
        self.assertEqual(self.client.post('/api/subjects/', {'name': '   '}, content_type='application/json').status_code, 400)
        r = self.client.post('/api/subjects/', {'name': ' Secret '}, content_type='application/json')  # another user's name is fine
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['name'], 'Secret')

    def test_summary_lists_only_own_subjects(self):
        rows = self.client.get('/api/subjects/summary/').json()
        self.assertEqual([r['name'] for r in rows], ['Database Systems'])
        self.assertEqual(rows[0]['materials_count'], 2)
        self.assertIn('updated_at', rows[0])

    def test_materials_have_names_summary_and_quiz_newest_first(self):
        rows = self.client.get(f'/api/subjects/{self.db.id}/materials/').json()
        self.assertEqual([r['filename'] for r in rows], ['new.docx', 'old.pdf'])
        self.assertEqual(rows[1]['summary'], '- B-trees stay balanced')
        self.assertEqual(rows[1]['quiz_id'], self.quiz.id)
        self.assertIsNone(rows[0]['quiz_id'])
        self.assertEqual(self.client.get(f'/api/subjects/{self.theirs.id}/materials/').status_code, 404)

    def test_flashcards_show_source_and_this_users_due_date(self):
        fresh = Flashcard.objects.create(subject=self.db, material=self.old, question='q1', answer='a')
        later = Flashcard.objects.create(subject=self.db, question='q2', answer='a')
        due_at = timezone.now() + timedelta(days=3)
        FlashcardReview.objects.create(user=self.user, flashcard=later, due_at=due_at)
        FlashcardReview.objects.create(user=self.other, flashcard=fresh, due_at=due_at)  # someone else's review never leaks in
        rows = {r['question']: r for r in self.client.get(f'/api/subjects/{self.db.id}/flashcards/').json()}
        self.assertIsNone(rows['q1']['due_at'])
        self.assertEqual(rows['q1']['material_name'], 'old.pdf')
        self.assertIsNotNone(rows['q2']['due_at'])
        self.assertIsNone(rows['q2']['material_name'])

    def test_quizzes_show_this_users_attempts(self):
        now = timezone.now()
        UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, is_completed=True, score=72, end_time=now - timedelta(days=1))
        UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, is_completed=True, score=45, end_time=now)
        UserQuizAttempt.objects.create(user=self.other, quiz=self.quiz, is_completed=True, score=100, end_time=now)
        row = self.client.get(f'/api/subjects/{self.db.id}/quizzes/').json()[0]
        self.assertEqual((row['attempts'], row['last_score'], row['best_score']), (2, 45, 72))
        self.assertEqual(row['material_name'], 'old.pdf')

    @patch('subjects.views.process_material.delay')
    @patch('subjects.views.MAX_UPLOAD_BYTES', 10)
    def test_upload_rejects_files_over_the_limit(self, delay):
        big = SimpleUploadedFile('big.pdf', b'%PDF' + b'x' * 7, content_type='application/pdf')
        r = self.client.post(f'/api/subjects/{self.db.id}/upload_material/', {'file': big})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {'file': ['Files can be up to 100 MB.']})
        delay.assert_not_called()

    def test_deleting_a_material_removes_its_file(self):
        with patch.object(FieldFile, 'delete') as delete_file:
            r = self.client.delete(f'/api/materials/{self.old.id}/')
        self.assertEqual(r.status_code, 204)
        delete_file.assert_called_once_with(save=False)
        self.assertFalse(SubjectMaterial.objects.filter(pk=self.old.pk).exists())
        theirs = SubjectMaterial.objects.create(subject=self.theirs, file='subject_materials/x.pdf', file_type='PDF')
        self.assertEqual(self.client.delete(f'/api/materials/{theirs.id}/').status_code, 404)
