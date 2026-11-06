"""Coverage map endpoints for the React app. Every lookup is scoped to request.user."""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .models import ContentChunk, Quiz, Section, Subject, UserQuizAttempt
from .quiz_api import _attempt_payload
from .services.coverage import Signals, _signals, judge, label, subject_coverage
from .services.sections import range_label
from .tasks import generate_dynamic_quiz_questions

logger = logging.getLogger(__name__)
SECTION_QUESTIONS = 5
MISSING = "This part of your notes doesn't exist any more. Its file may have been deleted."


@api_view(['GET'])
def subject_map(request, subject_id):
    """The % studied, one sentence, counts per status, and every file with its sections (no passage text, so it stays small)."""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    data = subject_coverage(request.user, subject)
    data.pop('rows')
    return Response(data)


def _own_section(request, section_id):
    section = (Section.objects.select_related('material__subject')
               .filter(id=section_id, material__subject__user=request.user, material__status='COMPLETED').first())
    if section is None:
        raise NotFound(MISSING)
    return section


def joined(texts, overlap=200):
    """Passages as one text: each one repeats up to 200 characters of the one before, so drop that repeat."""
    out = ''
    for t in texts:
        cut = next((n for n in range(min(len(out), len(t), overlap), 0, -1) if out.endswith(t[:n])), 0)
        out = f'{out} {t[cut:].lstrip()}'.strip() if not cut else out + t[cut:]
    return out.lstrip('.,;: ')


@api_view(['GET'])
def section_detail(request, section_id):
    """One section: its status and why, its passages, and what there is to study it with."""
    section = _own_section(request, section_id)
    material = section.material
    parts = material.sections.count()
    status_, reason, last = judge(_signals(request.user, [section]).get(section.id, Signals()))
    passages = list(ContentChunk.objects.filter(material=material, chunk_index__gte=section.first_chunk,
                                                chunk_index__lte=section.last_chunk).order_by('chunk_index')
                    .values('id', 'chunk_index', 'content'))
    return Response({
        'id': section.id, 'title': section.title, 'label': label(section, material.display_name, parts),
        'range': range_label(section, parts), 'status': status_, 'reason': reason, 'last_studied': last,
        'subject_id': material.subject_id, 'file': {'id': material.id, 'name': material.display_name},
        'cards': section.flashcards.count(),
        'text': joined([p['content'] for p in passages]),
        'passages': [{'chunk_id': p['id'], 'chunk_index': p['chunk_index'], 'material_name': material.display_name,
                      'content': p['content']} for p in passages],
    })


@api_view(['POST'])
def section_quiz(request, section_id):
    """Start 5 fresh questions written from this section only, on the file's quiz pages."""
    section = _own_section(request, section_id)
    material = section.material
    quiz = material.quizzes.order_by('id').first() or Quiz.objects.create(
        subject=material.subject, material=material, title=f'Quiz on {material.display_name}')
    # Fresh attempts left open on this quiz are closed, as starting new questions does elsewhere
    UserQuizAttempt.objects.filter(user=request.user, quiz=quiz, uses_dynamic_questions=True,
                                   end_time__isnull=True).update(is_completed=True, end_time=timezone.now())
    attempt = UserQuizAttempt.objects.create(user=request.user, quiz=quiz, uses_dynamic_questions=True, section=section)
    try:
        generate_dynamic_quiz_questions.delay(attempt.id, num_questions=SECTION_QUESTIONS)
    except Exception as e:  # broker down: there are no standard questions for one section to fall back to
        logger.error(f'Could not queue a section quiz for attempt {attempt.id}: {e}')
        attempt.delete()
        return Response({'detail': "XP couldn't start a quiz on this part just now. Try again in a moment."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(_attempt_payload(attempt), status=status.HTTP_201_CREATED)
