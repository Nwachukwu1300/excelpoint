"""Quiz endpoints for the React app. Every lookup is scoped to request.user."""

import logging
from collections import defaultdict

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Quiz, UserQuizAttempt
from .services.quizzes import attempt_status, grade, public_questions, review
from .tasks import generate_dynamic_quiz_questions

logger = logging.getLogger(__name__)
FRESH_QUESTIONS = 10


def _material_name(quiz):
    return quiz.material.display_name if quiz.material else None


def _quiz_info(quiz):
    return {'id': quiz.id, 'title': quiz.title, 'material_name': _material_name(quiz), 'subject_id': quiz.subject_id,
            'subject_name': quiz.subject.name, 'time_limit': quiz.time_limit, 'pass_score': quiz.pass_score}


def _attempt_payload(attempt):
    state = attempt_status(attempt)
    return {
        'id': attempt.id, 'status': state, 'fresh': attempt.uses_dynamic_questions,
        'started_at': attempt.start_time, 'quiz': _quiz_info(attempt.quiz),
        'questions': public_questions(attempt) if state == 'ready' else [],
    }


def _own_attempt(request, attempt_id):
    return get_object_or_404(UserQuizAttempt.objects.select_related('quiz__subject', 'quiz__material'),
                             id=attempt_id, user=request.user)


@api_view(['POST'])
def start_attempt(request, quiz_id):
    """Start a quiz: the standard questions, or {"fresh": true} for new ones written by XP in the background."""
    quiz = get_object_or_404(Quiz.objects.select_related('subject', 'material'), id=quiz_id, subject__user=request.user)
    fresh = request.data.get('fresh') is True
    if fresh:
        # Unfinished fresh attempts on this quiz are left behind for good
        UserQuizAttempt.objects.filter(user=request.user, quiz=quiz, uses_dynamic_questions=True,
                                       end_time__isnull=True).update(is_completed=True, end_time=timezone.now())
    attempt = UserQuizAttempt.objects.create(user=request.user, quiz=quiz, uses_dynamic_questions=fresh)
    if fresh:
        try:
            generate_dynamic_quiz_questions.delay(attempt.id, num_questions=FRESH_QUESTIONS)
        except Exception as e:  # broker down: the standard questions still work
            logger.error(f"Could not queue fresh questions for attempt {attempt.id}: {e}")
            attempt.uses_dynamic_questions = False
            attempt.save(update_fields=['uses_dynamic_questions'])
            return Response({**_attempt_payload(attempt), 'fell_back': True}, status=status.HTTP_201_CREATED)
    return Response(_attempt_payload(attempt), status=status.HTTP_201_CREATED)


@api_view(['GET'])
def attempt_detail(request, attempt_id):
    """Poll this while status is "generating"; questions never include the answers."""
    return Response(_attempt_payload(_own_attempt(request, attempt_id)))


@api_view(['POST'])
def submit_attempt(request, attempt_id):
    attempt = _own_attempt(request, attempt_id)
    state = attempt_status(attempt)
    if state != 'ready':
        return Response({'detail': f'This attempt is {state}, so it can’t be submitted.'}, status=status.HTTP_409_CONFLICT)
    answers = request.data.get('answers', {})
    if not isinstance(answers, dict):
        raise ValidationError({'answers': 'Send an object of question id → answer.'})
    grade(attempt, answers)
    return Response(_results_payload(attempt))


def _results_payload(attempt):
    rows = review(attempt)
    return {
        'id': attempt.id, 'quiz': _quiz_info(attempt.quiz), 'fresh': attempt.uses_dynamic_questions,
        'score': round(attempt.score or 0), 'passed': attempt.is_passed(),
        'earned_points': attempt.earned_points, 'total_points': attempt.total_points,
        'correct_count': sum(r['is_correct'] for r in rows), 'question_count': len(rows),
        'finished_at': attempt.end_time, 'questions': rows,
    }


@api_view(['GET'])
def attempt_results(request, attempt_id):
    attempt = _own_attempt(request, attempt_id)
    if attempt_status(attempt) != 'completed':
        return Response({'detail': 'Results appear once the quiz is submitted.'}, status=status.HTTP_409_CONFLICT)
    return Response(_results_payload(attempt))


@api_view(['GET'])
def history(request):
    """Finished attempts (newest first, ?subject=<id> to filter) and the average score per subject."""
    attempts = (UserQuizAttempt.objects.filter(user=request.user, is_completed=True, score__isnull=False)
                .select_related('quiz__subject', 'quiz__material').order_by('-end_time', '-id'))
    if request.GET.get('subject'):
        if not request.GET['subject'].isdigit():
            raise ValidationError({'subject': 'Must be a subject id.'})
        attempts = attempts.filter(quiz__subject_id=int(request.GET['subject']))
    attempts = list(attempts[:100])
    by_subject = defaultdict(list)
    for a in attempts:
        by_subject[(a.quiz.subject_id, a.quiz.subject.name)].append(a.score)
    return Response({
        'attempts': [
            {'id': a.id, 'quiz_id': a.quiz_id, 'quiz_title': _material_name(a.quiz) or a.quiz.title,
             'subject_id': a.quiz.subject_id, 'subject_name': a.quiz.subject.name, 'score': round(a.score),
             'passed': a.is_passed(), 'fresh': a.uses_dynamic_questions, 'finished_at': a.end_time}
            for a in attempts
        ],
        'subjects': [
            {'id': sid, 'name': name, 'average': round(sum(scores) / len(scores)), 'attempts': len(scores)}
            for (sid, name), scores in sorted(by_subject.items(), key=lambda kv: kv[0][1])
        ],
    })
