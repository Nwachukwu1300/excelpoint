"""The Coverage map: how much of a subject's material the student has studied, section by section.

Nothing is stored: each status is worked out from flashcard reviews, quiz answers and Explain it back
marks, so it changes as soon as the student studies, and goes when a file is deleted.

Statuses (the thresholds Lord Soma approved):
- not_studied: no flashcard review, quiz answer or explanation touches the section.
- shaky: the latest explanation that touched it had a mistake, or a card's last grade was Again or Hard,
  or under 70% of its last 5 quiz answers were right, or it was only right once.
- solid: right on 2+ separate occasions (a quiz attempt, a card review, or an explanation, which counts as 2).
- fading: would be solid, but nothing in 21 days, or one of its cards is more than a day overdue.
"""

from collections import defaultdict
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from ..models import ContentChunk, Flashcard, FlashcardReview, Question, Section, SubjectMaterial, UserAnswer, UserQuizAttempt
from .sections import range_label

FADING_DAYS = 21
OVERDUE_GRACE = timedelta(days=1)
QUIZ_WINDOW = 5
QUIZ_PASS = 0.7
STATUSES = ('not_studied', 'shaky', 'solid', 'fading')


def _date(dt):
    return f'{dt.day} {dt:%B}'


def _join(parts):
    return parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' and ' + parts[-1]


def _plural(n, word):
    return f'{n} {word}' if n == 1 else f'{n} {word}s'


class Signals:
    """Everything the student did that touches one section."""

    def __init__(self):
        self.quiz = []  # (at, correct, attempt_id)
        self.cards = []  # FlashcardReview rows
        self.explain = {}  # session_id -> {'at', 'right', 'wrong'}
        self.card_count = 0
        self.question_count = 0

    def empty(self):
        return not (self.quiz or any(r.last_reviewed_at for r in self.cards) or self.explain)


def judge(signals, now=None):
    """(status, reason, last activity) for one section's signals."""
    now = now or timezone.now()
    if signals.empty():
        reason = "You haven't seen a flashcard, quiz question or explanation from this part yet."
        if not signals.card_count and not signals.question_count:
            reason += ' It has no flashcards or quiz questions of its own, so take a quiz on it or explain it to XP.'
        return 'not_studied', reason, None

    reviewed = [r for r in signals.cards if r.last_reviewed_at]
    quiz = sorted(signals.quiz)
    sessions = sorted(signals.explain.items(), key=lambda kv: kv[1]['at'])
    times = [at for at, _, _ in quiz] + [r.last_reviewed_at for r in reviewed] + [s['at'] for _, s in sessions]
    last = max(times)

    # Occasions on which the student got it right; a mistake-free explanation is worth two
    occasions = len({attempt for _, correct, attempt in quiz if correct})
    occasions += sum(r.repetitions for r in reviewed)  # SM-2 repetitions: right in a row, one review each
    good_explains = [s for _, s in sessions if s['right'] and not s['wrong']]
    occasions += 2 * len(good_explains)

    problems = []
    latest_explain = sessions[-1][1] if sessions else None
    if latest_explain and latest_explain['wrong']:
        problems.append('your last explanation of this had a mistake')
    recent = quiz[-QUIZ_WINDOW:]
    missed = sum(1 for _, correct, _ in recent if not correct)
    if recent and (len(recent) - missed) / len(recent) < QUIZ_PASS:
        problems.append(f'you missed {missed} of {len(recent)} quiz questions on this')
    again = sum(1 for r in reviewed if r.last_grade == 1)
    hard = sum(1 for r in reviewed if r.last_grade == 3)
    if again:
        problems.append(f'you rated {_plural(again, "card")} Again')
    if hard:
        problems.append(f'you rated {"one card" if hard == 1 else f"{hard} cards"} Hard')
    if problems:
        text = _join(problems)
        return 'shaky', text[0].upper() + text[1:] + '.', last
    if occasions < 2:
        return 'shaky', 'You got this right once. Practise it again to make it solid.', last

    overdue = sum(1 for r in reviewed if r.due_at < now - OVERDUE_GRACE)
    if overdue:
        return 'fading', (f'{"One of its flashcards is" if overdue == 1 else f"{overdue} of its flashcards are"} overdue. '
                          'Review them before you forget.'), last
    if now - last > timedelta(days=FADING_DAYS):
        return 'fading', f"You knew this well, but you haven't practised it since {_date(last)}.", last
    extra = ', including a correct explanation' if good_explains else ''
    return 'solid', f'You got this right on {occasions} separate occasions{extra}. Most recently on {_date(last)}.', last


def _signals(user, sections):
    """Signals per section id, from a fixed number of queries."""
    by_id = {s.id: s for s in sections}
    signals = defaultdict(Signals)
    if not sections:
        return signals
    for r in FlashcardReview.objects.filter(user=user, flashcard__section__in=sections).select_related('flashcard'):
        signals[r.flashcard.section_id].cards.append(r)
    for section_id in Flashcard.objects.filter(section__in=sections).values_list('section_id', flat=True):
        signals[section_id].card_count += 1
    for section_id in Question.objects.filter(section__in=sections).values_list('section_id', flat=True):
        signals[section_id].question_count += 1
    for a in (UserAnswer.objects.filter(attempt__user=user, question__section__in=sections)
              .values('question__section_id', 'is_correct', 'answered_at', 'attempt_id')):
        signals[a['question__section_id']].quiz.append((a['answered_at'], a['is_correct'], a['attempt_id']))
    materials = {s.material_id for s in sections}
    attempts = (UserQuizAttempt.objects.filter(user=user, quiz__material_id__in=materials, uses_dynamic_questions=True,
                                               is_completed=True, score__isnull=False)
                .values('id', 'end_time', 'dynamic_questions'))
    for attempt in attempts:
        for q in attempt['dynamic_questions'] or []:
            if q.get('section_id') in by_id:
                signals[q['section_id']].question_count += 1
                if 'is_correct' in q:
                    signals[q['section_id']].quiz.append((attempt['end_time'], q['is_correct'], attempt['id']))

    from explain.models import ExplainTurn
    turns = list(ExplainTurn.objects.filter(session__user=user, session__subject_id__in={s.material.subject_id for s in sections},
                                            kind='explanation').values('session_id', 'created_at', 'marks'))
    chunk_ids = {m['passage']['chunk_id'] for t in turns for m in t['marks'] if m.get('passage')}
    where = {c['id']: (c['material_id'], c['chunk_index'])
             for c in ContentChunk.objects.filter(id__in=chunk_ids).values('id', 'material_id', 'chunk_index')}
    by_material = defaultdict(list)
    for s in sections:
        by_material[s.material_id].append(s)
    for t in turns:
        for m in t['marks']:
            if not m.get('passage') or m['passage']['chunk_id'] not in where or m['verdict'] == 'not_in_notes':
                continue
            material_id, index = where[m['passage']['chunk_id']]
            section = next((s for s in by_material[material_id] if s.first_chunk <= index <= s.last_chunk), None)
            if section:
                entry = signals[section.id].explain.setdefault(t['session_id'], {'at': t['created_at'], 'right': 0, 'wrong': 0})
                entry['at'] = max(entry['at'], t['created_at'])
                entry['right' if m['verdict'] == 'correct' else 'wrong'] += 1
    return signals


def label(section, file_name, parts):
    """The section's name as a student reads it: a range name gets its file, so "Pages 3–5 in notes.pdf"."""
    if section.title == range_label(section, parts):
        return f'{section.title} in {file_name}'
    return section.title


def _queue_build(material):
    """Files processed before the Coverage map get their sections in the background, once."""
    if cache.add(f'sections-queued:{material.id}', 1, 600):
        try:
            from ..tasks import build_material_sections
            build_material_sections.delay(material.id)
        except Exception:
            cache.delete(f'sections-queued:{material.id}')


def subject_coverage(user, subject, now=None):
    """The whole map for one subject: the %, the sentence, counts, and each file with its sections."""
    now = now or timezone.now()
    materials = list(SubjectMaterial.objects.filter(subject=subject).order_by('created_at', 'id'))
    sections = list(Section.objects.filter(material__in=materials).select_related('material'))
    signals = _signals(user, sections)
    by_material = defaultdict(list)
    for s in sections:
        by_material[s.material_id].append(s)

    files, rows, counts = [], [], dict.fromkeys(STATUSES, 0)
    for m in materials:
        state = {'PENDING': 'processing', 'PROCESSING': 'processing', 'FAILED': 'failed'}.get(m.status, 'ready')
        own = by_material.get(m.id, [])
        if state == 'ready' and not own:
            state = 'building'
            _queue_build(m)
        items = []
        for s in own:
            status, reason, last = judge(signals[s.id], now)
            size = s.last_chunk - s.first_chunk + 1
            counts[status] += 1
            item = {'id': s.id, 'title': s.title, 'label': label(s, m.display_name, len(own)), 'range': range_label(s, len(own)),
                    'status': status, 'reason': reason, 'size': size, 'last_studied': last,
                    'cards': signals[s.id].card_count, 'questions': signals[s.id].question_count}
            items.append(item)
            rows.append({**item, 'material_id': m.id, 'file': m.display_name})
        total = sum(i['size'] for i in items)
        studied = sum(i['size'] for i in items if i['status'] != 'not_studied')
        files.append({'id': m.id, 'name': m.display_name, 'state': state, 'error': m.error if state == 'failed' else '',
                      'percent': round(100 * studied / total) if total else None,
                      'studied': sum(1 for i in items if i['status'] != 'not_studied'), 'sections': items})

    total = sum(r['size'] for r in rows)
    studied = sum(r['size'] for r in rows if r['status'] != 'not_studied')
    percent = round(100 * studied / total) if total else 0
    return {
        'subject': {'id': subject.id, 'name': subject.name},
        'state': 'empty' if not materials else 'ready',
        'percent': percent,
        'sentence': _sentence(rows, studied) if rows else '',
        'counts': counts,
        'files': files,
        'rows': rows,  # flat, for suggestions and the data download; the API drops it
    }


def _sentence(rows, studied):
    untouched = sorted((r for r in rows if r['status'] == 'not_studied'), key=lambda r: -r['size'])
    fading = sorted((r for r in rows if r['status'] == 'fading'), key=lambda r: r['last_studied'])
    shaky = [r for r in rows if r['status'] == 'shaky']
    if untouched and not studied:
        return f"Start with {untouched[0]['label']}."
    if untouched:
        return f"{untouched[0]['label']} hasn't come up yet."
    if fading:
        return f"{fading[0]['label']} is fading. Review it soon."
    if shaky:
        return f"{shaky[0]['label']} needs more practice."
    return "Everything you've studied is solid."


def gaps(user, subjects, limit=3):
    """The most useful sections to study next across subjects: fading first, then untouched (biggest), then shaky."""
    rows = []
    for subject in subjects:
        for r in subject_coverage(user, subject)['rows']:
            rows.append({**r, 'subject_id': subject.id, 'subject_name': subject.name})
    order = {'fading': 0, 'not_studied': 1, 'shaky': 2}
    picked = sorted((r for r in rows if r['status'] in order),
                    key=lambda r: (order[r['status']], -r['size'] if r['status'] == 'not_studied' else 0,
                                   r['last_studied'] or timezone.now()))
    return picked[:limit]
