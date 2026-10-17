"""Stage 3/4 pages: quality dashboard and per-answer debug panel (server-rendered)."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .evaluation import quality_summary
from .views import user_sessions

STAGES = ['classification_ms', 'rewrite_ms', 'embedding_ms', 'search_ms', 'reranking_ms', 'generation_ms', 'verification_ms']


@login_required
def insights(request):
    try:
        days = max(1, min(365, int(request.GET.get('days', 30))))
    except ValueError:
        days = 30
    sessions = user_sessions(request.user)
    recent = sessions.prefetch_related('evaluations').order_by('-created_at')[:30]
    rows = []
    for s in recent:
        evals = {e.evaluator: e for e in s.evaluations.all()}
        rows.append({'session': s, 'heuristic': evals.get('heuristic'), 'judge': evals.get('llm_judge')})
    return render(request, 'reasoning/insights.html', {
        'summary': quality_summary(sessions, days=days),
        'rows': rows,
        'days': days,
    })


@login_required
def session_debug(request, session_id):
    session = get_object_or_404(user_sessions(request.user), session_id=session_id)
    trace = session.full_result or {}
    breakdown = session.latency_breakdown or {}
    total = session.total_latency or 0
    # embedding/search are parts of retrieval_ms, so show them instead of it when present
    stage_keys = [k for k in STAGES if k in breakdown] + sorted(k for k in breakdown if k.startswith('retry_'))
    if 'embedding_ms' not in breakdown and 'retrieval_ms' in breakdown:
        stage_keys.insert(2, 'retrieval_ms')
    stages = [
        {'name': k.removesuffix('_ms').replace('_', ' '), 'ms': breakdown[k],
         'pct': round(100 * breakdown[k] / total, 1) if total else 0}
        for k in stage_keys
    ]
    return render(request, 'reasoning/session_debug.html', {
        'session': session,
        'trace': trace,
        'chunks': session.chunks.filter(used_in_retry=False).order_by('-similarity_score'),
        'retry_chunks': session.chunks.filter(used_in_retry=True).order_by('-similarity_score'),
        'evaluations': session.evaluations.all(),
        'stages': stages,
        'prompts': trace.get('prompts', {}),
    })
