"""Group a file's passages into sections a student would recognise, for the Coverage map.

Stored passages have lost their headings and page breaks (clean_text collapses whitespace), so the
structure comes from the original file: Word headings, a PDF's outline or page groups, or 10-minute
ranges of a recording. Each passage then joins the section its middle falls in. Untitled sections are
named by one small AI call; if that fails, the range ("Pages 3–5") is the name.
"""

import json
import logging
import math
import shutil
import subprocess

import numpy as np
from django.conf import settings
from django.db import transaction

from ..models import ContentChunk, Flashcard, Question, Section
from ..utils import clean_text, load_embedding_model, local_file_path

logger = logging.getLogger(__name__)

MAX_SECTIONS = 15
TARGET_SECTIONS = 12  # for page groups and plain parts
WINDOW_SECONDS = 600  # 10 minutes of a recording


# ---- Segments: (title or None, kind, start, end, text) from the original file ----

def _docx_segments(path):
    import docx

    document = docx.Document(path)
    paragraphs = [(p.style.name if p.style is not None else '', p.text) for p in document.paragraphs]
    tables = [cell.text for table in document.tables for row in table.rows for cell in row.cells if cell.text.strip()]
    level = next((name for name in ('Heading 1', 'Heading 2')
                  if sum(1 for style, text in paragraphs if style == name and text.strip()) >= 2), None)
    segments, title, parts = [], None, []
    for style, text in paragraphs:
        if not text.strip():
            continue
        if level and style == level:
            if parts or title:
                segments.append([title, 'heading', None, None, '\n'.join(parts)])
            title, parts = text.strip()[:120], [text]
        else:
            parts.append(text)
    segments.append([title, 'heading' if title else 'part', None, None, '\n'.join(parts)])
    segments[-1][4] = '\n'.join([segments[-1][4]] + tables)  # tables come last in the passages too
    return segments


def _pdf_segments(path):
    from langchain_community.document_loaders import PyPDFLoader
    from pypdf import PdfReader

    pages = [p.page_content for p in PyPDFLoader(path).load()]  # the same reader the passages came from
    starts = []
    try:
        reader = PdfReader(path)
        for item in reader.outline:
            if not isinstance(item, list):  # top level only; nested lists are sub-chapters
                starts.append((reader.get_destination_page_number(item), str(item.title).strip()[:120]))
    except Exception:
        starts = []
    starts = sorted({page: title for page, title in starts if 0 <= page < len(pages)}.items())
    if len(starts) >= 2:
        if starts[0][0] > 0:
            starts.insert(0, (0, None))
        bounds = [(p, t) for p, t in starts]
        return [[title, 'heading' if title else 'pages', page + 1, (bounds[i + 1][0] if i + 1 < len(bounds) else len(pages)),
                 ' '.join(pages[page:bounds[i + 1][0] if i + 1 < len(bounds) else len(pages)])]
                for i, (page, title) in enumerate(bounds)]
    size = max(1, math.ceil(len(pages) / min(TARGET_SECTIONS, max(1, math.ceil(len(pages) / 4)))))
    return [[None, 'pages', i + 1, min(i + size, len(pages)), ' '.join(pages[i:i + size])] for i in range(0, len(pages), size)]


def _locate(segments, chunks):
    """Which segment each passage belongs to (by its middle), or None if the passages can't be found in the file's text."""
    texts = [clean_text(s[4]) for s in segments]
    full = ' '.join(texts)
    ends, at = [], 0
    for t in texts:
        at += len(t) + 1
        ends.append(at)
    owners, pos = [], 0
    for chunk in chunks:
        found = full.find(chunk.content, pos)
        if found < 0:
            return None  # the file changed or reads differently now
        middle = found + len(chunk.content) / 2
        owners.append(next(i for i, end in enumerate(ends) if middle < end or i == len(ends) - 1))
        pos = found + 1
    return owners


def _duration(path):
    if not shutil.which('ffprobe'):
        return None
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                           capture_output=True, text=True, timeout=60)
    try:
        return float(probe.stdout.strip())
    except ValueError:
        return None


def _groups(n_chunks, owners=None):
    """Runs of passage indexes per owner, in order; empty owners drop out."""
    groups = []
    for i in range(n_chunks):
        owner = owners[i] if owners else None
        if groups and groups[-1][0] == owner:
            groups[-1][1].append(i)
        else:
            groups.append((owner, [i]))
    return groups


def plan_sections(material, chunks, path=None):
    """Section dicts (title, kind, start, end, first, last) for a file's passages, in order. `chunks` are ordered."""
    n = len(chunks)
    if n == 0:
        return []
    plans = []
    if material.file_type in ('AUDIO', 'VIDEO'):
        duration = _duration(path) if path else None
        if duration:
            window = max(WINDOW_SECONDS, math.ceil(duration / MAX_SECTIONS / 60) * 60)
            # shortcut: no timestamps from the transcription model, so a passage's time is estimated from its position
            owners = [min(int((i + 0.5) / n * duration // window), math.ceil(duration / window) - 1) for i in range(n)]
            for w, idx in _groups(n, owners):
                plans.append({'title': None, 'kind': 'time', 'start': w * window, 'end': min((w + 1) * window, duration),
                              'first': idx[0], 'last': idx[-1]})
    elif path and material.file_type in ('PDF', 'DOCX', 'DOC'):
        try:
            segments = _pdf_segments(path) if material.file_type == 'PDF' else _docx_segments(path)
            owners = _locate(segments, chunks)
        except Exception:
            logger.exception('Could not read sections from material %s', material.id)
            owners = None
        if owners is not None:
            for s, idx in _groups(n, owners):
                title, kind, start, end, _ = segments[s]
                plans.append({'title': title, 'kind': kind, 'start': start, 'end': end, 'first': idx[0], 'last': idx[-1]})
    if not plans:  # no file, an unknown type, or text that no longer matches: even parts
        size = max(1, math.ceil(n / min(TARGET_SECTIONS, max(1, math.ceil(n / 4)))))
        plans = [{'title': None, 'kind': 'part', 'start': None, 'end': None, 'first': i, 'last': min(i + size, n) - 1}
                 for i in range(0, n, size)]
    while len(plans) > MAX_SECTIONS:  # merge the smallest neighbouring pair
        i = min(range(len(plans) - 1), key=lambda k: plans[k + 1]['last'] - plans[k]['first'])
        a, b = plans[i], plans.pop(i + 1)
        a.update(last=b['last'], end=b['end'] if b['end'] is not None else a['end'],
                 title=a['title'] or b['title'])
    if len(plans) == 1:
        plans[0]['kind'] = 'whole'
    return plans


def _clock(seconds):
    """Whole minutes as 9:00 or 1:05:00."""
    minutes = int(round(seconds / 60))
    return f'{minutes // 60}:{minutes % 60:02d}:00' if minutes >= 60 else f'{minutes}:00'


def range_label(section, parts=None):
    """"Pages 3–5", "About 10:00–20:00" or "Part 2 of 4"; None for a heading or a whole file."""
    if section.kind == 'pages' and section.start:
        start, end = int(section.start), int(section.end or section.start)
        return f'Page {start}' if start == end else f'Pages {start}–{end}'
    if section.kind == 'time' and section.start is not None:
        return f'About {_clock(section.start)}–{_clock(section.end or section.start)}'
    if section.kind == 'part' and parts:
        return f'Part {section.order + 1} of {parts}'
    return None


def _name(plans, chunks):
    """Short names for untitled sections, from one AI call. Returns {index: name}; empty if the call can't run."""
    untitled = [i for i, p in enumerate(plans) if not p['title']]
    if not untitled or not settings.OPENAI_API_KEY:
        return {}
    from openai import OpenAI

    texts = {str(i): ' '.join(c.content for c in chunks[plans[i]['first']:plans[i]['last'] + 1])[:600] for i in untitled}
    try:
        response = OpenAI(api_key=settings.OPENAI_API_KEY).chat.completions.create(
            model=settings.OPENAI_MODEL, temperature=0.2, max_completion_tokens=400, response_format={'type': 'json_object'},
            messages=[{'role': 'system', 'content': 'You name sections of a student\'s study notes. Use only the text given. '
                                                    'Each name is 2 to 5 plain words in sentence case, like "Light reactions" or '
                                                    '"How B-trees stay balanced". Reply with JSON: {"names": {"<id>": "<name>"}}.'},
                      {'role': 'user', 'content': json.dumps(texts)}],
        )
        names = json.loads(response.choices[0].message.content or '{}').get('names') or {}
    except Exception:
        logger.exception('Naming sections failed')
        return {}
    return {int(k): str(v).strip().rstrip('.')[:80] for k, v in names.items() if str(k).isdigit() and str(v).strip()}


def build_sections(material):
    """Replace a file's sections from its passages and stored file, then link its flashcards and quiz questions."""
    chunks = list(ContentChunk.objects.filter(material=material).order_by('chunk_index'))
    path_ctx = local_file_path(material.file) if material.file else None
    try:
        if path_ctx:
            with path_ctx as path:
                plans = plan_sections(material, chunks, path)
        else:
            plans = plan_sections(material, chunks)
    except (FileNotFoundError, OSError):
        plans = plan_sections(material, chunks)  # the stored file is gone; the passages still are
    names = _name(plans, chunks)
    with transaction.atomic():
        Section.objects.filter(material=material).delete()
        sections = Section.objects.bulk_create([
            Section(material=material, order=i, kind=p['kind'], start=p['start'], end=p['end'],
                    first_chunk=chunks[p['first']].chunk_index, last_chunk=chunks[p['last']].chunk_index,
                    title=(p['title'] or names.get(i) or '')[:120])
            for i, p in enumerate(plans)
        ])
        for s in sections:
            if not s.title:
                s.title = range_label(s, len(sections)) or material.display_name
        Section.objects.bulk_update(sections, ['title'])
    link_items(material)
    return sections


def section_for_chunk(sections, chunk_index):
    return next((s for s in sections if s.first_chunk <= chunk_index <= s.last_chunk), None)


def nearest_sections(material, texts, sections=None):
    """For each text, the section of the file's closest passage (local embeddings, no AI call)."""
    sections = sections if sections is not None else list(material.sections.all())
    chunks = [c for c in ContentChunk.objects.filter(material=material, embedding_vector__isnull=False).order_by('chunk_index')]
    if not texts or not sections or not chunks:
        return [None] * len(texts)
    if len(sections) == 1:
        return [sections[0]] * len(texts)
    passages = np.array([np.asarray(c.embedding_vector, dtype=float) for c in chunks])
    queries = np.asarray(load_embedding_model().encode(list(texts)), dtype=float)
    passages /= np.linalg.norm(passages, axis=1, keepdims=True) + 1e-9
    queries /= np.linalg.norm(queries, axis=1, keepdims=True) + 1e-9
    best = (queries @ passages.T).argmax(axis=1)
    return [section_for_chunk(sections, chunks[i].chunk_index) for i in best]


def link_items(material):
    """Point the file's flashcards and quiz questions at the section they test."""
    sections = list(material.sections.all())
    cards = list(Flashcard.objects.filter(material=material))
    questions = list(Question.objects.filter(quiz__material=material).prefetch_related('answers', 'choices'))

    def question_text(q):
        right = [c.text for c in q.choices.all() if c.is_correct] + [a.text for a in q.answers.all() if a.is_correct]
        return ' '.join([q.text] + right + [q.explanation or ''])

    for item, section in zip(cards, nearest_sections(material, [f'{c.question} {c.answer}' for c in cards], sections)):
        item.section = section
    for item, section in zip(questions, nearest_sections(material, [question_text(q) for q in questions], sections)):
        item.section = section
    Flashcard.objects.bulk_update(cards, ['section'])
    Question.objects.bulk_update(questions, ['section'])
