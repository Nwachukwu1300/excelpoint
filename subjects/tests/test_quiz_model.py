from django.contrib.auth import get_user_model
from django.test import TestCase

from subjects.models import Quiz, Subject


class QuizSubjectTest(TestCase):
    def test_quiz_belongs_to_subject(self):
        user = get_user_model().objects.create_user(username='u', password='p')
        subject = Subject.objects.create(user=user, name='Maths')
        quiz = Quiz.objects.create(subject=subject, title='Q1')

        self.assertEqual(str(quiz), 'Q1 - Maths')
        self.assertEqual(list(Quiz.objects.filter(subject__user=user)), [quiz])
        self.assertEqual(list(subject.quizzes.all()), [quiz])
