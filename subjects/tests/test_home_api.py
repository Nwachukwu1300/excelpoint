from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from subjects.models import (ChatMessage, ChatSession, Flashcard, Quiz, Subject, SubjectMaterial,
                             UserQuizAttempt)

User = get_user_model()


class HomeApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s', password='p')
        self.other = User.objects.create_user('o', password='p')
        self.db = Subject.objects.create(user=self.user, name='Databases')
        self.maths = Subject.objects.create(user=self.user, name='Maths')
        material = SubjectMaterial.objects.create(subject=self.db, file='subject_materials/sql.pdf', file_type='PDF', status='COMPLETED')
        for i in range(3):
            Flashcard.objects.create(subject=self.db, question=f'q{i}', answer='a')
        quiz = Quiz.objects.create(subject=self.db, material=material, title='SQL')
        now = timezone.now()
        UserQuizAttempt.objects.create(user=self.user, quiz=quiz, is_completed=True, score=80, end_time=now - timedelta(days=2))
        UserQuizAttempt.objects.create(user=self.user, quiz=quiz, is_completed=True, score=45.4, end_time=now)
        UserQuizAttempt.objects.create(user=self.user, quiz=quiz, is_completed=False)  # in progress: ignored

        talked = ChatSession.objects.create(user=self.user, subject=self.db, title='B-tree indexes')
        ChatMessage.objects.create(session=talked, role='user', content='What is a B-tree?')
        ChatSession.objects.create(user=self.user, subject=self.maths)  # no messages: not shown

        theirs = Subject.objects.create(user=self.other, name='Secret')
        Flashcard.objects.create(subject=theirs, question='x', answer='y')
        their_chat = ChatSession.objects.create(user=self.other, subject=theirs, title='Not yours')
        ChatMessage.objects.create(session=their_chat, role='user', content='hi')

    def test_today_payload(self):
        self.client.force_login(self.user)
        data = self.client.get('/api/home/').json()

        self.assertEqual(data['due'], {'count': 3, 'subjects': 1, 'minutes': 2})
        self.assertEqual([c['title'] for c in data['recent_chats']], ['B-tree indexes'])
        self.assertEqual(data['recent_chats'][0]['subject_name'], 'Databases')

        self.assertEqual([s['name'] for s in data['subjects']], ['Databases', 'Maths'])  # most due first
        subjects = {s['name']: s for s in data['subjects']}
        self.assertEqual(subjects['Databases'], {'id': self.db.id, 'name': 'Databases', 'materials_count': 1,
                                                 'due_count': 3, 'last_quiz_score': 45})  # latest attempt, not best
        self.assertIsNone(subjects['Maths']['last_quiz_score'])

        kinds = {s['kind']: s for s in data['suggestions']}
        self.assertEqual(kinds['weak_quiz']['subject_id'], self.db.id)
        self.assertIsNotNone(kinds['weak_quiz']['quiz_id'])
        self.assertEqual(kinds['review']['subject_id'], self.db.id)
        self.assertEqual(kinds['empty_subject']['subject_id'], self.maths.id)
        self.assertNotIn('priority', kinds['review'])

    def test_new_user_gets_an_empty_but_valid_payload(self):
        self.client.force_login(User.objects.create_user('new', password='p'))
        self.assertEqual(self.client.get('/api/home/').json(), {
            'due': {'count': 0, 'subjects': 0, 'minutes': 0}, 'suggestions': [], 'recent_chats': [], 'subjects': [],
        })

    def test_anonymous_is_403(self):
        self.assertEqual(self.client.get('/api/home/').status_code, 403)
