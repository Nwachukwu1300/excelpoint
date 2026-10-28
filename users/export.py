"""Everything a user has in ExcelPoint, as one zip: data.json plus their uploaded files."""

import json
import re
import shutil
import tempfile
import zipfile

from django.core.serializers.json import DjangoJSONEncoder

from subjects.models import ChatSession, FlashcardReview, UserQuizAttempt
from .models import UserProfile


def _safe(name):
    """A name that is safe as one part of a path inside the zip (no folders, no "..")."""
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name).strip(' .') or 'file'


def build_export(user):
    """Write the user's export to an anonymous temp file and return it, rewound. The caller closes it."""
    profile = UserProfile.objects.filter(user=user).first()
    reviews = {r.flashcard_id: r for r in FlashcardReview.objects.filter(user=user)}
    data = {
        'account': {
            'username': user.username, 'email': user.email, 'first_name': user.first_name, 'last_name': user.last_name,
            'education_level': profile.education_level if profile else '', 'joined': user.date_joined,
        },
        'subjects': [],
        'quiz_attempts': [
            {'quiz': a.quiz.title, 'subject': a.quiz.subject.name, 'started': a.start_time, 'finished': a.end_time,
             'score': a.score, 'completed': a.is_completed}
            for a in UserQuizAttempt.objects.filter(user=user).select_related('quiz__subject').order_by('start_time')
        ],
        'conversations': [
            {'subject': s.subject.name, 'title': s.title, 'started': s.created_at,
             'messages': [{'role': m.role, 'text': m.content, 'at': m.timestamp} for m in s.messages.order_by('timestamp')]}
            for s in ChatSession.objects.filter(user=user).select_related('subject').order_by('created_at')
        ],
        'notifications': [
            {'title': n.title, 'body': n.body, 'at': n.created_at, 'read': n.read_at is not None}
            for n in user.notifications.order_by('created_at')
        ],
    }

    out = tempfile.TemporaryFile()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for subject in user.subjects.order_by('name').prefetch_related('materials__chunks', 'flashcards'):
            folder = f'files/{subject.id}-{_safe(subject.name)}'
            materials = []
            for m in subject.materials.order_by('created_at'):
                path = f'{folder}/{m.id}-{_safe(m.display_name)}' if m.file else None
                if path:
                    try:
                        with m.file.open('rb') as src, zf.open(path, 'w') as dst:
                            shutil.copyfileobj(src, dst)
                    except (FileNotFoundError, OSError):
                        path = None  # the stored file is gone; its text and summary are still exported
                materials.append({
                    'name': m.display_name, 'type': m.file_type, 'status': m.status, 'uploaded': m.created_at,
                    'file_in_zip': path, 'summary': m.summary,
                    'text': '\n\n'.join(c.content for c in sorted(m.chunks.all(), key=lambda c: c.chunk_index)),
                })
            data['subjects'].append({
                'name': subject.name, 'created': subject.created_at, 'files': materials,
                'flashcards': [
                    {'question': f.question, 'answer': f.answer,
                     'next_review': reviews[f.id].due_at if f.id in reviews else None}
                    for f in subject.flashcards.order_by('created_at')
                ],
            })
        zf.writestr('data.json', json.dumps(data, cls=DjangoJSONEncoder, indent=2, ensure_ascii=False))
        zf.writestr('README.txt', 'Your ExcelPoint data.\n\ndata.json: your account, subjects, file text and summaries, '
                                  'flashcards, quiz results, XP conversations and notifications.\n'
                                  'files/: the files you uploaded, one folder per subject.\n')
    out.seek(0)
    return out
