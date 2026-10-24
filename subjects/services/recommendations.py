"""
Adaptive study suggestions from the user's own history: what's due, where quiz scores
are weak, what hasn't been practised, and questions their materials couldn't answer.
"""

from datetime import timedelta

from django.db.models import Count, Max
from django.urls import reverse
from django.utils import timezone

from ..models import ChatMessage, Quiz, Subject, UserQuizAttempt
from .spaced_repetition import due_cards

WEAK_SCORE = 70  # percent
GAP_WINDOW_DAYS = 14


def _material_name(material):
    return material.file.name.rsplit('/', 1)[-1] if material else 'this material'


def recommend(user, limit=6):
    """Suggestions sorted by priority (higher first): dicts of kind, title, reason, url, priority,
    subject_id and quiz_id (None unless the suggestion is about a quiz). `url` points at the old pages;
    the React app builds its own links from the ids."""
    recs = []

    # 1. Flashcards due (spaced repetition)
    # order_by() clears due_cards' ordering, which Django would otherwise add to GROUP BY
    for row in due_cards(user).order_by().values('subject_id', 'subject__name').annotate(n=Count('id', distinct=True)):
        recs.append({
            'kind': 'review', 'priority': 50 + min(row['n'], 40),
            'title': f"Review {row['n']} flashcard{'s' if row['n'] != 1 else ''} in {row['subject__name']}",
            'reason': "They're due now; reviewing on schedule is what makes them stick.",
            'url': reverse('review_flashcards', args=[row['subject_id']]),
            'subject_id': row['subject_id'], 'quiz_id': None,
        })

    # 2. Weak quizzes: latest completed attempt under the threshold
    attempts = UserQuizAttempt.objects.filter(user=user, is_completed=True, score__isnull=False)
    for quiz_id in attempts.values('quiz_id').annotate(last=Max('end_time')).values_list('quiz_id', flat=True):
        last = attempts.filter(quiz_id=quiz_id).select_related('quiz__material', 'quiz__subject').order_by('-end_time', '-id').first()
        if last.score < WEAK_SCORE:
            recs.append({
                'kind': 'weak_quiz', 'priority': 40 + round(WEAK_SCORE - last.score),
                'title': f"Retake the quiz on {_material_name(last.quiz.material)}",
                'reason': f"Your last score was {last.score:.0f}%. Each retake asks new questions from the same material.",
                'url': reverse('take_quiz', args=[quiz_id]),
                'subject_id': last.quiz.subject_id, 'quiz_id': quiz_id,
            })

    # 3. Quizzes never attempted
    for quiz in (Quiz.objects.filter(subject__user=user)
                 .exclude(attempts__user=user)
                 .select_related('material')[:3]):
        recs.append({
            'kind': 'untried_quiz', 'priority': 30,
            'title': f"Test yourself on {_material_name(quiz.material)}",
            'reason': "You haven't tried this quiz yet.",
            'url': reverse('take_quiz', args=[quiz.id]),
            'subject_id': quiz.subject_id, 'quiz_id': quiz.id,
        })

    # 4. Knowledge gaps: recent questions the materials couldn't answer (strict-RAG fallbacks)
    since = timezone.now() - timedelta(days=GAP_WINDOW_DAYS)
    fallbacks = (ChatMessage.objects
                 .filter(session__user=user, role='assistant', timestamp__gte=since,
                         metadata__model_info__pipeline='fallback')
                 .select_related('session__subject').order_by('-timestamp')[:20])
    gaps = {}
    for answer in fallbacks:
        question = (ChatMessage.objects.filter(session=answer.session, role='user', timestamp__lte=answer.timestamp)
                    .order_by('-timestamp').values_list('content', flat=True).first())
        gaps.setdefault(answer.session.subject, []).append(question)
    for subject, questions in gaps.items():
        example = next((q for q in questions if q), '')
        recs.append({
            'kind': 'knowledge_gap', 'priority': 35 + len(questions),
            'title': f"Add materials to {subject.name}",
            'reason': (f"{len(questions)} recent question{'s weren’t' if len(questions) != 1 else ' wasn’t'} covered by your notes"
                       + (f", e.g. “{example[:80]}”." if example else ".")),
            'url': reverse('subject_detail', args=[subject.id]),
            'subject_id': subject.id, 'quiz_id': None,
        })

    # 5. Subjects with nothing uploaded yet
    for subject in Subject.objects.filter(user=user).annotate(n=Count('materials')).filter(n=0)[:2]:
        recs.append({
            'kind': 'empty_subject', 'priority': 20,
            'title': f"Upload your first material to {subject.name}",
            'reason': "XP can only answer, quiz and make flashcards from what you upload.",
            'url': reverse('subject_detail', args=[subject.id]),
            'subject_id': subject.id, 'quiz_id': None,
        })

    recs.sort(key=lambda r: r['priority'], reverse=True)
    return recs[:limit]
