from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from subjects.models import Quiz, Subject
from subjects.utils import short_answer_matches


class QuizSubjectTest(TestCase):
    def test_quiz_belongs_to_subject(self):
        user = get_user_model().objects.create_user(username='u', password='p')
        subject = Subject.objects.create(user=user, name='Maths')
        quiz = Quiz.objects.create(subject=subject, title='Q1')

        self.assertEqual(str(quiz), 'Q1 - Maths')
        self.assertEqual(list(Quiz.objects.filter(subject__user=user)), [quiz])
        self.assertEqual(list(subject.quizzes.all()), [quiz])


class ShortAnswerGradingTest(SimpleTestCase):
    def test_exact_match_ignoring_case_spacing_and_punctuation(self):
        self.assertTrue(short_answer_matches('  data  definition LANGUAGE. ', ['Data Definition Language']))

    def test_substrings_and_blanks_do_not_score(self):
        self.assertFalse(short_answer_matches('a', ['Data Definition Language']))
        self.assertFalse(short_answer_matches('', ['Data Definition Language']))
        self.assertFalse(short_answer_matches(None, ['x']))
