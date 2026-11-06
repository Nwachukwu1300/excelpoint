"""
Adaptive study suggestions from the user's own history: what's due, where quiz scores
are weak, what hasn't been practised, and questions their materials couldn't answer.
"""

from datetime import timedelta

from django.db.models import Count, Max
from django.urls import reverse
from django.utils import timezone

from ..models import ChatMessage, Quiz, Subject, UserQuizAttempt

WEAK_SCORE = 70  # percent
GAP_WINDOW_DAYS = 14


def _material_name(material):
    return material.display_name if material else 'this file'


def recommend(user, limit=6):
    """Suggestions sorted by priority (higher first): dicts of kind, title, reason, url, priority,
    subject_id and quiz_id (None unless the suggestion is about a quiz). `url` points at the old pages;
    the React app builds its own links from the ids."""
    recs = []

    # Cards to review aren't suggested: Home's review card already leads with them

    # 2. Weak quizzes: latest completed attempt under the threshold
    attempts = UserQuizAttempt.objects.filter(user=user, is_completed=True, score__isnull=False)
    for quiz_id in attempts.values('quiz_id').annotate(last=Max('end_time')).values_list('quiz_id', flat=True):
        last = attempts.filter(quiz_id=quiz_id).select_related('quiz__material', 'quiz__subject').order_by('-end_time', '-id').first()
        if last.score < WEAK_SCORE:
            recs.append({
                'kind': 'weak_quiz', 'priority': 40 + round(WEAK_SCORE - last.score),
                'title': f"Retake the quiz on {_material_name(last.quiz.material)}",
                'reason': f"Your last score was {last.score:.0f}%. Each retake asks new questions from the same file.",
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
        if (answer.metadata.get('model_info') or {}).get('files_ready') is False:
            continue  # asked before any file was ready: not a gap in the files
        question = (ChatMessage.objects.filter(session=answer.session, role='user', timestamp__lte=answer.timestamp)
                    .order_by('-timestamp').values_list('content', flat=True).first())
        gaps.setdefault(answer.session.subject, []).append(question)
    for subject, questions in gaps.items():
        example = next((q for q in questions if q), '')
        recs.append({
            'kind': 'knowledge_gap', 'priority': 35 + len(questions),
            'title': f"Add files to {subject.name}?",
            'reason': (f"XP found nothing in your files for {len(questions)} recent question{'s' if len(questions) != 1 else ''}"
                       + (f", for example “{example[:80]}”" if example else "")
                       + ". If that's part of this subject, upload notes that cover it."),
            'url': reverse('subject_detail', args=[subject.id]),
            'subject_id': subject.id, 'quiz_id': None,
        })

    # 5. Coverage gaps: fading sections, then the biggest untouched ones, then shaky ones (at most 3)
    from .coverage import gaps
    titles = {'fading': 'Refresh {label}', 'not_studied': 'Start {label}', 'shaky': 'Practise {label}'}
    reasons = {'not_studied': "Nothing from this part of {file} has come up yet. Explain it to XP or take a quick quiz on it."}
    ready = Subject.objects.filter(user=user, materials__status='COMPLETED').distinct()
    for rank, gap in enumerate(gaps(user, ready)):
        recs.append({
            'kind': 'coverage_gap', 'status': gap['status'],
            # Fading and untouched parts outrank everything else (weak quizzes top out at 110)
            'priority': {'fading': 130, 'not_studied': 120, 'shaky': 36}[gap['status']] - rank,
            'title': titles[gap['status']].format(label=gap['label']),
            'reason': reasons.get(gap['status'], gap['reason']).format(file=gap['file']),
            'url': reverse('subject_detail', args=[gap['subject_id']]),
            'subject_id': gap['subject_id'], 'quiz_id': None, 'section_id': gap['id'],
        })

    # 6. Subjects with nothing uploaded yet
    for subject in Subject.objects.filter(user=user).annotate(n=Count('materials')).filter(n=0)[:2]:
        recs.append({
            'kind': 'empty_subject', 'priority': 20,
            'title': f"Upload your first file to {subject.name}",
            'reason': "XP can only answer, quiz and make flashcards from what you upload.",
            'url': reverse('subject_detail', args=[subject.id]),
            'subject_id': subject.id, 'quiz_id': None,
        })

    recs.sort(key=lambda r: r['priority'], reverse=True)
    return recs[:limit]
