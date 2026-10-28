from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from subjects.models import Answer, Choice, Question, Quiz, Subject, SubjectMaterial, UserQuizAttempt
from subjects.tasks import _give_up

User = get_user_model()
FRESH = [
    {'id': 'dynamic_1', 'text': 'Which tree stays balanced?', 'type': 'multiple_choice', 'points': 1, 'explanation': 'B-trees rebalance.',
     'choices': [{'id': 'dynamic_1_choice_1', 'text': 'B-tree', 'is_correct': True}, {'id': 'dynamic_1_choice_2', 'text': 'Heap', 'is_correct': False}]},
    {'id': 'dynamic_2', 'text': 'Name the index type for ranges', 'type': 'short_answer', 'points': 1, 'correct_answers': ['B-tree']},
]


class QuizApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tq', password='p')
        self.client.force_login(self.user)
        subject = Subject.objects.create(user=self.user, name='Databases')
        material = SubjectMaterial.objects.create(subject=subject, file='subject_materials/lecture4.pdf', file_type='PDF')
        self.quiz = Quiz.objects.create(subject=subject, material=material, title='Lecture 4')
        self.mc = Question.objects.create(quiz=self.quiz, text='Balanced?', question_type='multiple_choice', order=1, explanation='Leaves share a depth.')
        self.right = Choice.objects.create(question=self.mc, text='Yes', is_correct=True)
        self.wrong = Choice.objects.create(question=self.mc, text='No', is_correct=False)
        self.short = Question.objects.create(quiz=self.quiz, text='What is DDL?', question_type='short_answer', order=2)
        Answer.objects.create(question=self.short, text='Data Definition Language', is_correct=True)

    def start(self, fresh=False):
        return self.client.post(f'/api/quiz/{self.quiz.id}/attempts/', {'fresh': fresh}, content_type='application/json')

    def test_standard_quiz_shows_questions_without_answers(self):
        data = self.start().json()
        self.assertEqual(data['status'], 'ready')
        self.assertEqual(data['quiz']['material_name'], 'lecture4.pdf')
        self.assertEqual([q['text'] for q in data['questions']], ['Balanced?', 'What is DDL?'])
        self.assertEqual(data['questions'][0]['choices'], [{'id': str(self.right.id), 'text': 'Yes'}, {'id': str(self.wrong.id), 'text': 'No'}])
        self.assertNotIn('is_correct', str(data))
        self.assertNotIn('Data Definition', str(data))

    def test_submit_scores_every_question_and_explains(self):
        attempt = self.start().json()['id']
        r = self.client.post(f'/api/quiz/attempts/{attempt}/submit/', {'answers': {str(self.mc.id): str(self.right.id)}}, content_type='application/json')
        data = r.json()
        self.assertEqual((data['score'], data['correct_count'], data['question_count']), (50, 1, 2))  # the skipped one counts
        rows = {q['text']: q for q in data['questions']}
        self.assertEqual(rows['Balanced?'], {'id': str(self.mc.id), 'text': 'Balanced?', 'type': 'multiple_choice', 'points': 1,
                                             'your_answer': 'Yes', 'correct_answer': 'Yes', 'is_correct': True, 'explanation': 'Leaves share a depth.'})
        self.assertEqual(rows['What is DDL?']['correct_answer'], 'Data Definition Language')
        self.assertEqual(self.client.get(f'/api/quiz/attempts/{attempt}/results/').json()['score'], 50)
        # it's finished: can't be submitted twice
        again = self.client.post(f'/api/quiz/attempts/{attempt}/submit/', {'answers': {}}, content_type='application/json')
        self.assertEqual(again.status_code, 409)

    def test_short_answers_and_wrong_choices(self):
        attempt = self.start().json()['id']
        data = self.client.post(f'/api/quiz/attempts/{attempt}/submit/', {'answers': {
            str(self.mc.id): str(self.wrong.id), str(self.short.id): 'data definition language'}}, content_type='application/json').json()
        rows = {q['text']: q for q in data['questions']}
        self.assertFalse(rows['Balanced?']['is_correct'])
        self.assertTrue(rows['What is DDL?']['is_correct'])
        self.assertEqual(data['score'], 50)

    @patch('subjects.quiz_api.generate_dynamic_quiz_questions')
    def test_fresh_questions_are_queued_then_polled_on_the_same_attempt(self, task):
        data = self.start(fresh=True).json()
        self.assertEqual(data['status'], 'generating')
        task.delay.assert_called_once_with(data['id'], num_questions=10)
        task.assert_not_called()  # never run inside the request

        attempt = UserQuizAttempt.objects.get(id=data['id'])
        attempt.dynamic_questions = FRESH
        attempt.save()
        polled = self.client.get(f'/api/quiz/attempts/{attempt.id}/').json()
        self.assertEqual(UserQuizAttempt.objects.count(), 1)  # polling doesn't start another attempt
        self.assertEqual(polled['status'], 'ready')
        self.assertEqual([c['text'] for c in polled['questions'][0]['choices']], ['B-tree', 'Heap'])
        self.assertNotIn('is_correct', str(polled))
        self.assertNotIn('correct_answers', str(polled))

        results = self.client.post(f'/api/quiz/attempts/{attempt.id}/submit/', {'answers': {
            'dynamic_1': 'dynamic_1_choice_1', 'dynamic_2': 'heap'}}, content_type='application/json').json()
        self.assertEqual((results['score'], results['correct_count']), (50, 1))
        self.assertEqual(results['questions'][1]['correct_answer'], 'B-tree')
        self.assertEqual(results['questions'][1]['your_answer'], 'heap')

    @patch('subjects.quiz_api.generate_dynamic_quiz_questions')
    def test_failed_generation_is_reported(self, task):
        attempt_id = self.start(fresh=True).json()['id']
        _give_up(attempt_id)
        self.assertEqual(self.client.get(f'/api/quiz/attempts/{attempt_id}/').json()['status'], 'failed')

    @patch('subjects.quiz_api.generate_dynamic_quiz_questions')
    def test_queue_down_falls_back_to_the_standard_questions(self, task):
        task.delay.side_effect = ConnectionError('broker down')
        data = self.start(fresh=True).json()
        self.assertTrue(data['fell_back'])
        self.assertEqual(data['status'], 'ready')
        self.assertEqual(len(data['questions']), 2)

    @patch('subjects.quiz_api.generate_dynamic_quiz_questions')
    def test_starting_fresh_again_abandons_the_unfinished_one(self, task):
        first = self.start(fresh=True).json()['id']
        self.start(fresh=True)
        self.assertEqual(self.client.get(f'/api/quiz/attempts/{first}/').json()['status'], 'abandoned')

    def test_history_lists_finished_attempts_with_subject_averages(self):
        now = timezone.now()
        UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, is_completed=True, score=40, end_time=now - timedelta(days=1))
        UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, is_completed=True, score=80, end_time=now)
        UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz, is_completed=True, end_time=now)  # abandoned: no score
        data = self.client.get('/api/quiz/attempts/').json()
        self.assertEqual([a['score'] for a in data['attempts']], [80, 40])
        self.assertEqual(data['attempts'][0]['quiz_title'], 'lecture4.pdf')
        self.assertEqual(data['subjects'], [{'id': self.quiz.subject_id, 'name': 'Databases', 'average': 60, 'attempts': 2}])
        self.assertEqual(self.client.get(f'/api/quiz/attempts/?subject={self.quiz.subject_id + 999}').json()['attempts'], [])

    def test_everything_is_owner_scoped(self):
        attempt = self.start().json()['id']
        intruder = Client()
        intruder.force_login(User.objects.create_user('x', password='p'))
        self.assertEqual(intruder.post(f'/api/quiz/{self.quiz.id}/attempts/', {}, content_type='application/json').status_code, 404)
        for url in [f'/api/quiz/attempts/{attempt}/', f'/api/quiz/attempts/{attempt}/results/']:
            self.assertEqual(intruder.get(url).status_code, 404)
        self.assertEqual(intruder.post(f'/api/quiz/attempts/{attempt}/submit/', {}, content_type='application/json').status_code, 404)
        self.assertEqual(intruder.get('/api/quiz/attempts/').json()['attempts'], [])

    def test_starting_again_resumes_an_unfinished_attempt(self):
        first = self.start()
        self.assertEqual(first.status_code, 201)
        quizzes = self.client.get(f'/api/subjects/{self.quiz.subject_id}/quizzes/').json()
        self.assertIs(quizzes[0]['has_unfinished_attempt'], True)
        again = self.start()
        self.assertEqual((again.status_code, again.json()['id']), (200, first.json()['id']))
        self.client.post(f"/api/quiz/attempts/{first.json()['id']}/submit/", {'answers': {}}, content_type='application/json')
        self.assertEqual(self.start().status_code, 201)  # finished: a new attempt
        self.assertTrue(self.client.get(f'/api/subjects/{self.quiz.subject_id}/quizzes/').json()[0]['has_unfinished_attempt'])  # the new one

    def test_a_missing_quiz_says_so_plainly(self):
        for response in [self.client.get('/api/quiz/attempts/999999/'),
                         self.client.post('/api/quiz/999999/attempts/', {}, content_type='application/json')]:
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()['detail'], "This quiz doesn't exist, or it was deleted.")

    def test_the_generation_job_marks_its_own_failure(self):
        from subjects.tasks import generate_dynamic_quiz_questions
        orphan = Quiz.objects.create(subject=self.quiz.subject, title='No material')  # nothing to write questions from
        attempt = UserQuizAttempt.objects.create(user=self.user, quiz=orphan, uses_dynamic_questions=True)
        self.assertEqual(generate_dynamic_quiz_questions(attempt.id)['status'], 'error')  # run inline
        attempt.refresh_from_db()
        self.assertEqual(attempt.dynamic_questions, [])
        self.assertEqual(self.client.get(f'/api/quiz/attempts/{attempt.id}/').json()['status'], 'failed')
