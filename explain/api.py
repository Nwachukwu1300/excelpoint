"""Explain it back endpoints for the React app. Every lookup is scoped to request.user."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from reasoning.models import ReasoningSession
from subjects.models import Subject

from . import service, voice
from .models import ExplainSession, ExplainTurn

logger = logging.getLogger(__name__)
MISSING = "This session doesn't exist, or it was deleted."
NO_FILES = 'Upload notes to this subject first. XP checks your explanation against them.'
MAX_TEXT = 4000
MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 3 minutes at the app's 24 kbps is about 0.5 MB


class AudioThrottle(UserRateThrottle):
    scope = 'explain_audio'  # transcriptions and spoken replies; checks have their own daily limit


def _limit(user):
    used, resets_at = service.checks_today(user)
    return {'used': used, 'limit': settings.EXPLAIN_DAILY_LIMIT, 'resets_at': resets_at}


def _turn(t):
    return {'id': t.id, 'mode': t.mode, 'kind': t.kind, 'student_text': t.student_text, 'reply': t.reply,
            'answer': t.answer, 'marks': t.marks, 'trace_id': t.reasoning_session_id, 'created_at': t.created_at}


def _session(s, full=True):
    data = {'id': s.id, 'topic': s.topic, 'subject_id': s.subject_id, 'finished': s.finished,
            'coverage': s.coverage, 'accuracy': s.accuracy, 'created_at': s.created_at}
    if full:
        turns = list(s.turns.all())
        data.update({
            'subject_name': s.subject.name, 'material_name': s.material.display_name if s.material else None,
            'key_points': s.key_points, 'turns': [_turn(t) for t in turns], 'voice': voice.provider(),
            'max_rounds': settings.EXPLAIN_MAX_ROUNDS, 'summary': service.summary(s) if s.finished else None,
            'limit': _limit(s.user),
        })
    else:
        data['rounds'] = s.turns.count()
    return data


def _own(request, session_id):
    s = ExplainSession.objects.select_related('subject', 'material', 'user').filter(id=session_id, user=request.user).first()
    if s is None:
        raise NotFound(MISSING)
    return s


@api_view(['GET', 'POST'])
def subject_sessions(request, subject_id):
    """GET: what the student can explain (files and topics from their summaries) and past sessions.
    POST {topic} or {material_id}: start a session, or {covered: false, suggestions} when the files don't cover it."""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    if request.method == 'GET':
        files = service.ready_files(subject).order_by('-created_at')
        return Response({
            'files_ready': files.exists(),
            'files': [{'id': m.id, 'name': m.display_name} for m in files],
            'topics': service.summary_topics(files, limit=8),
            'sessions': [_session(s, full=False) for s in subject.explain_sessions.filter(user=request.user)],
            'limit': _limit(request.user),
        })

    topic = str(request.data.get('topic') or '').strip()
    material = None
    if request.data.get('material_id'):
        material = service.ready_files(subject).filter(id=request.data.get('material_id')).first()
        if material is None:
            raise ValidationError({'material_id': "This file isn't ready, or it was deleted."})
    elif not 3 <= len(topic) <= 200:
        raise ValidationError({'topic': 'Type a topic of 3 to 200 characters.'})
    try:
        session = service.start(request.user, subject, topic=topic, material=material)
    except service.NotReady:
        return Response({'detail': NO_FILES}, status=status.HTTP_409_CONFLICT)
    if session is None:
        return Response({'covered': False, 'topic': topic, 'suggestions': service.close_topics(subject, topic)})
    return Response(_session(session), status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE'])
def session_detail(request, session_id):
    s = _own(request, session_id)
    if request.method == 'DELETE':
        traces = [t for t in s.turns.values_list('reasoning_session_id', flat=True) if t]
        ReasoningSession.objects.filter(session_id__in=traces).delete()
        s.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(_session(s))


@api_view(['POST'])
def add_turn(request, session_id):
    """Check one message {text, mode}. Counts toward the daily limit."""
    s = _own(request, session_id)
    if s.finished:
        return Response({'detail': 'This session has finished. Start a new one to explain again.'}, status=status.HTTP_409_CONFLICT)
    text = str(request.data.get('text') or '').strip()
    if not text:
        raise ValidationError({'text': 'Say or type your explanation first.'})
    if len(text) > MAX_TEXT:
        raise ValidationError({'text': f'Keep it under {MAX_TEXT} characters. Try explaining one part at a time.'})
    mode = request.data.get('mode') if request.data.get('mode') in ('voice', 'text') else 'text'
    try:
        with transaction.atomic():
            # One check at a time per student, so two at once can't both slip under the daily limit
            get_user_model().objects.select_for_update().filter(pk=request.user.pk).first()
            limit = _limit(request.user)
            if limit['used'] >= limit['limit']:
                return Response({'detail': f"You've used today's {limit['limit']} checks.", 'resets_at': limit['resets_at']},
                                status=status.HTTP_429_TOO_MANY_REQUESTS)
            service.check_turn(s, text, mode)
    except Exception:
        logger.exception('Explain check failed for session %s', s.id)
        return Response({'detail': "XP couldn't check that just now. Your explanation is still here; try again in a moment."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    s.refresh_from_db()
    return Response(_session(s))


@api_view(['POST'])
@throttle_classes([AudioThrottle])
def transcribe(request, session_id):
    """A recording (multipart 'audio') to text, so the student can check what XP heard. The audio isn't kept."""
    s = _own(request, session_id)
    audio = request.FILES.get('audio')
    if audio is None or audio.size == 0:
        raise ValidationError({'audio': 'No recording came through. Record again.'})
    if audio.size > MAX_AUDIO_BYTES:
        raise ValidationError({'audio': 'This recording is too long. Keep it under 3 minutes.'})
    if not settings.OPENAI_API_KEY:
        return Response({'detail': "Voice isn't available right now. Type your explanation instead."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    try:
        text = service.transcribe_clip(audio, s.topic)
    except service.Unclear:
        return Response({'detail': "XP couldn't make out any words. Check your mic is on, speak a little closer and try again."},
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except Exception:
        logger.exception('Explain transcription failed for session %s', s.id)
        return Response({'detail': "XP couldn't turn that recording into text. Record again, or type instead."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({'text': text})


@api_view(['POST'])
def finish(request, session_id):
    s = _own(request, session_id)
    if not s.finished:
        service.finish(s)
    return Response(_session(s))


@api_view(['GET'])
@throttle_classes([AudioThrottle])
def speech(request, turn_id):
    """XP's reply as audio when XP_VOICE is a server voice; 204 means the app speaks it itself."""
    turn = ExplainTurn.objects.filter(id=turn_id, session__user=request.user).first()
    if turn is None:
        raise NotFound(MISSING)
    try:
        audio = voice.speak(turn.reply)
    except Exception:
        logger.exception('Speech failed for turn %s', turn.id)
        audio = None  # the app falls back to the device's voice
    if not audio:
        return HttpResponse(status=204)
    response = HttpResponse(audio, content_type='audio/mpeg')
    response['Cache-Control'] = 'private, max-age=86400'
    return response
