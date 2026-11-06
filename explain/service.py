"""Explain it back: find the passages for a topic, check the student's statements against them, and score the session."""

import json
import logging
import re
import time
from datetime import timedelta

import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openai import OpenAI
from pgvector.django import CosineDistance

from reasoning.models import ReasoningSession, ReasoningSessionChunk
from reasoning.prompts import EXPLAIN_SYSTEM_PROMPT, EXPLAIN_USER_PROMPT_TEMPLATE
from subjects.models import ContentChunk, SubjectMaterial
from subjects.utils import load_embedding_model

from .models import ExplainSession, ExplainTurn

logger = logging.getLogger(__name__)

THRESHOLD = 0.3  # the same relevance gate as chat
TOPIC_PASSAGES = 6
MAX_PASSAGES = 10
REPLY_WORDS = 60  # about 20 seconds spoken
VERDICTS = ('correct', 'wrong', 'not_in_notes')
KINDS = ('explanation', 'question', 'off_topic')


class NotReady(Exception):
    """The subject has no processed files to check against."""


def ready_files(subject):
    return SubjectMaterial.objects.filter(subject=subject, status='COMPLETED')


def _embed(texts):
    return load_embedding_model().encode(texts)


def search(text, subject_id, top_k, material_id=None):
    """The subject's chunks closest to text, as passage dicts with a similarity score."""
    chunks = ContentChunk.objects.filter(material__subject_id=subject_id, material__status='COMPLETED',
                                         embedding_vector__isnull=False)
    if material_id:
        chunks = chunks.filter(material_id=material_id)
    vector = [float(x) for x in _embed(text)]
    with transaction.atomic():
        with transaction.get_connection().cursor() as cursor:
            cursor.execute("SET LOCAL hnsw.iterative_scan = 'relaxed_order'")  # keep scanning past the subject filter
        rows = list(chunks.select_related('material').annotate(distance=CosineDistance('embedding_vector', vector))
                    .order_by('distance')[:top_k])
    return [{'chunk_id': c.id, 'material_id': c.material_id, 'material_name': c.material.display_name,
             'chunk_index': c.chunk_index, 'content': c.content, 'similarity': round(1 - c.distance, 4)} for c in rows]


def summary_topics(materials, limit=None):
    """Short topics from each file's summary bullets (written when the file was processed), so no AI call."""
    topics, seen = [], set()
    for material in materials:
        for line in (material.summary or '').splitlines():
            if not re.match(r'\s*(?:[-*•]|\d+[.)])\s+', line):
                continue
            bold = re.search(r'\*\*(.+?)\*\*', line)
            text = bold.group(1) if bold else re.sub(r'^\s*(?:[-*•]|\d+[.)])\s+', '', line)
            text = re.sub(r'[*_`]', '', text).strip().rstrip('.:')
            if len(text) > 70:
                text = text[:70].rsplit(' ', 1)[0]
            text = text[:1].upper() + text[1:]
            if len(text) >= 3 and text.lower() not in seen:
                seen.add(text.lower())
                topics.append(text)
    return topics[:limit] if limit else topics


def close_topics(subject, topic, limit=4):
    """Covered topics nearest to one that isn't covered, ranked with the local embedding model."""
    candidates = summary_topics(ready_files(subject))[:60]
    if not candidates:
        return []
    vectors = _embed([topic] + candidates)
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    scores = vectors[1:] @ vectors[0]
    return [candidates[i] for i in np.argsort(-scores)[:limit]]


def start(user, subject, topic='', material=None):
    """A new session, or None when the topic isn't in the student's files."""
    if not ready_files(subject).exists():
        raise NotReady
    if material:
        topic = material.display_name
        # A file's summary says what the file is about; search within that file only
        passages = search(material.summary or topic, subject.id, TOPIC_PASSAGES, material_id=material.id)
    else:
        passages = [p for p in search(topic, subject.id, TOPIC_PASSAGES) if p['similarity'] >= THRESHOLD]
    if not passages:
        return None
    return ExplainSession.objects.create(user=user, subject=subject, material=material, topic=topic[:200], passages=passages)


def checks_today(user):
    """How many checks the student has used in the last 24 hours, and when the oldest of them expires."""
    since = timezone.now() - timedelta(hours=24)
    turns = ExplainTurn.objects.filter(session__user=user, created_at__gte=since)
    oldest = turns.order_by('created_at').values_list('created_at', flat=True).first()
    return turns.count(), (oldest + timedelta(hours=24)) if oldest else None


def _client():
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _norm(text):
    return ' '.join(re.sub(r'[^\w\s]', ' ', text.lower()).split())


def _history(session):
    lines = []
    for turn in session.turns.all():
        lines.append(f'Student: {turn.student_text}')
        lines.append(f'XP: {turn.reply}')
    return '\n'.join(lines) or '(this is the first message)'


def _short(text, words=REPLY_WORDS):
    parts = text.split()
    if len(parts) <= words:
        return text.strip()
    cut = ' '.join(parts[:words])
    end = max(cut.rfind('.'), cut.rfind('?'), cut.rfind('!'))
    return cut[:end + 1] if end > len(cut) // 2 else cut + '…'


def _clean(data, labelled, key_points, first):
    """Keep only what the passages back up: unknown passage ids can't support a mark."""
    kind = data.get('kind') if data.get('kind') in KINDS else 'explanation'
    marks = []
    for s in (data.get('statements') or []) if kind == 'explanation' else []:
        sentence = str(s.get('text') or '').strip()
        if not sentence:
            continue
        verdict = s.get('verdict') if s.get('verdict') in VERDICTS else 'not_in_notes'
        passage = labelled.get(str(s.get('passage') or '').strip())
        if verdict != 'not_in_notes' and not passage:
            verdict = 'not_in_notes'  # a mark XP can't show the evidence for isn't a mark
        quote = str(s.get('quote') or '').strip()
        if passage and _norm(quote) not in _norm(passage['content']):
            quote = ''  # the app highlights the closest sentence instead
        marks.append({
            'sentence': sentence, 'verdict': verdict,
            'note': str(s.get('note') or '').strip() if verdict == 'wrong' else '',
            'quote': quote if passage else '',
            'passage': {k: passage[k] for k in ('chunk_id', 'material_name', 'chunk_index', 'content')} if verdict != 'not_in_notes' else None,
        })
    if first:
        key_points = []
        for i, k in enumerate((data.get('key_points') or [])[:6], 1):
            passage = labelled.get(str(k.get('passage') or '').strip())
            if str(k.get('point') or '').strip() and passage:
                key_points.append({'id': f'K{i}', 'point': str(k['point']).strip(), 'covered': False,
                                   'passage': {key: passage[key] for key in ('chunk_id', 'material_name', 'chunk_index', 'content')}})
    covered = {str(c).strip() for c in data.get('covered') or []}
    for k in key_points:
        k['covered'] = k['covered'] or k['id'] in covered
    return kind, marks, key_points, _short(str(data.get('reply') or '')), str(data.get('answer') or '').strip() if kind == 'question' else ''


def check_turn(session, text, mode='text'):
    """Check one message from the student: one AI call, then save the turn and its trace."""
    started = time.monotonic()
    passages = {p['chunk_id']: p for p in session.passages}
    for p in search(text, session.subject_id, 4):
        if p['similarity'] >= THRESHOLD:
            passages.setdefault(p['chunk_id'], p)
    passages = list(passages.values())[:MAX_PASSAGES]
    labelled = {f'P{i}': p for i, p in enumerate(passages, 1)}
    search_ms = (time.monotonic() - started) * 1000

    first = not session.key_points
    if first:
        points = 'KEY POINTS: none yet. From the passages, list the 3 to 6 most important key points about the topic, with ids K1, K2 and so on in order.'
    else:
        points = 'KEY POINTS (ids for "covered"; leave "key_points" empty):\n' + '\n'.join(
            f"{k['id']}: {k['point']}{' (already covered)' if k['covered'] else ''}" for k in session.key_points)
    rounds = session.turns.count() + 1
    user_prompt = EXPLAIN_USER_PROMPT_TEMPLATE.format(
        topic=session.topic,
        passages='\n\n'.join(f"[{label} - {p['material_name']}]\n{p['content'][:1500]}" for label, p in labelled.items()),
        key_points=points, history=_history(session), message=text,
        last_round=('This is the last round: do not ask a question; tell them their summary is ready.'
                    if rounds >= settings.EXPLAIN_MAX_ROUNDS else ''),
    )
    checked = time.monotonic()
    response = _client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{'role': 'system', 'content': EXPLAIN_SYSTEM_PROMPT}, {'role': 'user', 'content': user_prompt}],
        temperature=0.2, max_completion_tokens=1500, response_format={'type': 'json_object'},
    )
    raw = response.choices[0].message.content or '{}'
    check_ms = (time.monotonic() - checked) * 1000
    kind, marks, key_points, reply, answer = _clean(json.loads(raw), labelled, session.key_points, first)
    if not reply:
        raise ValueError('The check came back without a reply')

    correct = sum(m['verdict'] == 'correct' for m in marks)
    wrong = sum(m['verdict'] == 'wrong' for m in marks)
    with transaction.atomic():
        trace = ReasoningSession.objects.create(
            kind='explain', subject_id=session.subject_id, original_query=text, classification_category=kind,
            pipeline_name='explain', retrieved_chunk_count=len(passages), generated_answer=reply, final_answer=reply,
            faithfulness_score=correct / (correct + wrong) if correct + wrong else None,
            total_latency=(time.monotonic() - started) * 1000,
            latency_breakdown={'search_ms': round(search_ms, 1), 'verification_ms': round(check_ms, 1)},
            full_result={'prompts': {'check': [{'role': 'system', 'content': EXPLAIN_SYSTEM_PROMPT},
                                               {'role': 'user', 'content': user_prompt}]}, 'raw_response': raw,
                         'explain': {'topic': session.topic, 'kind': kind, 'marks': marks, 'key_points': key_points}},
        )
        ReasoningSessionChunk.objects.bulk_create(ReasoningSessionChunk(
            session=trace, chunk_id=p['chunk_id'], chunk_text=p['content'], chunk_index=p['chunk_index'],
            material_id=p['material_id'], material_name=p['material_name'], similarity_score=p.get('similarity') or 0.0,
        ) for p in passages)
        turn = ExplainTurn.objects.create(session=session, mode=mode, kind=kind, student_text=text, reply=reply,
                                          answer=answer, marks=marks, reasoning_session_id=trace.session_id)
        session.key_points = key_points
        session.save(update_fields=['key_points'])
        if rounds >= settings.EXPLAIN_MAX_ROUNDS:
            finish(session)
    return turn


def summary(session):
    """What they nailed, got wrong and missed, from every check in the session."""
    marks = [m for t in session.turns.all() for m in t.marks]
    return {
        'nailed': [m for m in marks if m['verdict'] == 'correct'],
        'wrong': [m for m in marks if m['verdict'] == 'wrong'],
        'not_in_notes': [m for m in marks if m['verdict'] == 'not_in_notes'],
        'missed': [k for k in session.key_points if not k['covered']],
    }


def finish(session):
    marks = [m for t in session.turns.all() for m in t.marks]
    correct = sum(m['verdict'] == 'correct' for m in marks)
    wrong = sum(m['verdict'] == 'wrong' for m in marks)
    points = session.key_points
    session.accuracy = correct / (correct + wrong) if correct + wrong else None
    session.coverage = sum(k['covered'] for k in points) / len(points) if points else None
    session.finished = True
    session.finished_at = timezone.now()
    session.save(update_fields=['accuracy', 'coverage', 'finished', 'finished_at'])
    return session


class Unclear(Exception):
    """Nothing usable was heard in a recording."""


def transcribe_clip(upload, topic):
    """A short recording (up to 3 minutes) to text. It's sent as it is, so ffmpeg isn't needed; nothing is stored."""
    text = _client().audio.transcriptions.create(
        model=settings.EXPLAIN_TRANSCRIBE_MODEL,
        file=(upload.name or 'clip.webm', upload.read(), upload.content_type or 'audio/webm'),
        prompt=f'A student explaining {topic} from their study notes.',  # helps with the subject's own terms
    ).text.strip()
    if len(re.findall(r'\w+', text)) < 3:
        raise Unclear
    return text
