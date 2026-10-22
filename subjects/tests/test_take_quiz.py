from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.template.defaultfilters import escapejs
from django.test import TestCase
from django.urls import reverse

from subjects.models import Question, Quiz, Subject, UserQuizAttempt

QUESTIONS = [{'id': 'q1', 'text': 'What is DDL?', 'type': 'short_answer', 'points': 1, 'correct_answers': ['x']}]


class DynamicQuizTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('tq', password='p')
        self.client.force_login(user)
        self.quiz = Quiz.objects.create(subject=Subject.objects.create(user=user, name='S'), title='Q')
        self.url = reverse('take_quiz', args=[self.quiz.id])

    @patch('subjects.views.generate_dynamic_quiz_questions')
    def test_generation_is_queued_not_run_in_the_request(self, task):
        response = self.client.get(self.url, {'dynamic': 'true'})

        attempt = UserQuizAttempt.objects.get()
        task.delay.assert_called_once_with(attempt.id, num_questions=10)
        task.assert_not_called()  # never called synchronously
        self.assertTrue(response.context['loading_dynamic'])
        # the poller must come back to THIS attempt, or it would abandon it and start another
        self.assertEqual(response.context['refresh_url'], f'{self.url}?dynamic=true&attempt_id={attempt.id}')
        self.assertContains(response, f"window.location.href = '{escapejs(response.context['refresh_url'])}'")

    @patch('subjects.views.generate_dynamic_quiz_questions')
    def test_coming_back_when_ready_shows_questions_without_a_new_attempt(self, task):
        self.client.get(self.url, {'dynamic': 'true'})
        attempt = UserQuizAttempt.objects.get()
        attempt.dynamic_questions = QUESTIONS
        attempt.save()

        response = self.client.get(self.url, {'dynamic': 'true', 'attempt_id': attempt.id})

        self.assertEqual(UserQuizAttempt.objects.count(), 1)
        self.assertEqual(response.context['questions'], QUESTIONS)
        task.delay.assert_called_once()

    @patch('subjects.views.generate_dynamic_quiz_questions')
    def test_queue_down_falls_back_to_static_questions(self, task):
        task.delay.side_effect = ConnectionError('broker down')
        Question.objects.create(quiz=self.quiz, text='Static?', question_type='short_answer', order=1)

        response = self.client.get(self.url, {'dynamic': 'true'})

        self.assertFalse(response.context['loading_dynamic'])
        self.assertTrue(response.context['api_error'])
        self.assertContains(response, 'Static?')
