"""JSON endpoints for the new React app (/app/). Every query is scoped to request.user."""

import math
from collections import Counter

from django.db.models import Count, Max, OuterRef, Subquery

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import ChatSession, Flashcard, FlashcardReview, Subject, UserQuizAttempt
from .services.recommendations import recommend
from .services.spaced_repetition import REVIEW_GRADES, due_cards, preview_intervals, record_review

REVIEW_BATCH = 50  # cards per review session; the rest come back next time

SECONDS_PER_CARD = 27  # rough review pace for the "about N minutes" estimate


def due_by_subject(user):
    return Counter(due_cards(user).order_by().values_list('subject_id', flat=True))


def subject_summaries(user, due):
    """Subjects with material count, due cards, latest quiz score and last update; most cards due first."""
    last_score = (UserQuizAttempt.objects
                  .filter(user=user, quiz__subject=OuterRef('pk'), is_completed=True, score__isnull=False)
                  .order_by('-end_time', '-id').values('score')[:1])
    subjects = (user.subjects
                .annotate(materials_count=Count('materials', distinct=True), last_quiz_score=Subquery(last_score),
                          latest_upload=Max('materials__created_at'))
                .order_by('name'))
    rows = [
        {'id': s.id, 'name': s.name, 'materials_count': s.materials_count, 'due_count': due.get(s.id, 0),
         'last_quiz_score': None if s.last_quiz_score is None else round(s.last_quiz_score),
         'updated_at': max(filter(None, [s.updated_at, s.latest_upload]))}
        for s in subjects
    ]
    return sorted(rows, key=lambda r: -r['due_count'])  # stable, so ties stay alphabetical


@api_view(['GET'])
def home(request):
    """The "Today" page: what's due, ranked suggestions, recent chats, and subjects."""
    user = request.user
    due = due_by_subject(user)
    count = sum(due.values())
    chats = (ChatSession.objects.filter(user=user)
             .annotate(n=Count('messages')).filter(n__gt=0)
             .select_related('subject').order_by('-last_activity')[:3])
    return Response({
        'due': {'count': count, 'subjects': len(due), 'minutes': math.ceil(count * SECONDS_PER_CARD / 60)},
        'suggestions': [
            {k: r[k] for k in ('kind', 'title', 'reason', 'url', 'subject_id', 'quiz_id')}
            for r in recommend(user, limit=5)
        ],
        'recent_chats': [
            {'id': c.id, 'title': c.title if c.title and c.title != 'New conversation' else 'Untitled conversation',
             'subject_id': c.subject_id, 'subject_name': c.subject.name, 'last_activity': c.last_activity}
            for c in chats
        ],
        'subjects': subject_summaries(user, due),
    })


@api_view(['GET'])
def review_queue(request):
    """Cards due now (one subject with ?subject=<id>, otherwise all), each with how long every grade would push it back."""
    user = request.user
    subject = None
    if request.GET.get('subject'):
        if not request.GET['subject'].isdigit():
            raise ValidationError({'subject': 'Must be a subject id.'})
        subject = get_object_or_404(Subject, id=int(request.GET['subject']), user=user)
    due = due_cards(user, subject).select_related('subject', 'material')
    cards = list(due[:REVIEW_BATCH])
    reviews = {r.flashcard_id: r for r in FlashcardReview.objects.filter(user=user, flashcard__in=cards)}
    return Response({
        'due_count': due.count(),
        'subject': {'id': subject.id, 'name': subject.name} if subject else None,
        'grades': [{'grade': g, 'label': label} for g, label in REVIEW_GRADES],
        'cards': [
            {
                'id': c.id, 'question': c.question, 'answer': c.answer,
                'subject_id': c.subject_id, 'subject_name': c.subject.name,
                'material_name': c.material.display_name if c.material else None,
                'next_days': preview_intervals(reviews.get(c.id) or FlashcardReview()),
            }
            for c in cards
        ],
    })


@api_view(['POST'])
def review_grade(request):
    """Grade one card (SM-2) and say when it comes back."""
    try:
        grade = int(request.data.get('grade'))
        card_id = int(request.data.get('flashcard_id'))
    except (TypeError, ValueError):
        raise ValidationError({'detail': 'Send flashcard_id and grade as numbers.'})
    if grade not in dict(REVIEW_GRADES):
        raise ValidationError({'grade': f'Must be one of {sorted(dict(REVIEW_GRADES))}.'})
    card = get_object_or_404(Flashcard, id=card_id, subject__user=request.user)
    review = record_review(request.user, card, grade)
    return Response({'flashcard_id': card.id, 'interval_days': review.interval_days, 'due_at': review.due_at})
