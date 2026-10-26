"""Insights and answer-trace JSON for the React app (/app/insights). Scoped to the user's own subjects."""

import json

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from subjects.models import ChatMessage, Subject

from .evaluation import quality_summary
from .pages import STAGES
from .views import user_sessions

RANGES = (7, 30, 90)


def _is_follow_up(s):
    """The pipeline stores a 'rewritten' query even when nothing was rewritten."""
    return bool(s.rewritten_query) and s.rewritten_query.strip() != s.original_query.strip()


def _days(request):
    try:
        days = int(request.GET.get('days', 30))
    except ValueError:
        days = 30
    return days if days in RANGES else 30


@api_view(['GET'])
def insights(request):
    """Answer quality over the last 7/30/90 days, what needs attention, and the latest answers."""
    sessions = user_sessions(request.user)
    days = _days(request)
    names = dict(Subject.objects.filter(user=request.user).values_list('id', 'name'))
    recent = []
    for s in sessions.prefetch_related('evaluations').order_by('-created_at')[:20]:
        recent.append({
            'session_id': str(s.session_id), 'question': s.original_query, 'subject_name': names.get(s.subject_id, ''),
            'category': 'Follow-up' if _is_follow_up(s) else 'Standalone', 'chunks': s.retrieved_chunk_count,
            'confidence': s.confidence_score, 'unverified': s.unverified, 'no_context': not s.retrieved_chunk_count,
            'latency_ms': round(s.total_latency) if s.total_latency else None, 'created_at': s.created_at,
        })
    return Response({'summary': quality_summary(sessions, days=days), 'recent': recent})


def _claims(verification):
    """Claim lists: stored directly by VerificationResult.to_dict, or only inside the verifier's raw JSON reply."""
    verification = verification or {}
    if 'supported_claims' in verification or 'unsupported_claims' in verification:
        return verification.get('supported_claims') or [], verification.get('unsupported_claims') or []
    try:
        raw = json.loads(verification.get('raw_response') or '{}')
    except (TypeError, ValueError):
        raw = {}
    return raw.get('supported_claims') or [], raw.get('unsupported_claims') or []


def _chunk(c):
    return {'material_name': c.material_name, 'chunk_index': c.chunk_index, 'similarity': c.similarity_score,
            'rerank': c.reranking_score, 'text': c.chunk_text}


@api_view(['GET'])
def trace(request, session_id):
    """Everything about one answer: the query, the excerpts, prompts, verification, retries, scores and timings."""
    s = get_object_or_404(user_sessions(request.user), session_id=session_id)
    result = s.full_result or {}
    breakdown = s.latency_breakdown or {}
    total = s.total_latency or 0
    # embedding/search are parts of retrieval_ms, so show them instead of it when present (as the old debug page did)
    keys = [k for k in STAGES if k in breakdown] + sorted(k for k in breakdown if k.startswith('retry_'))
    if 'embedding_ms' not in breakdown and 'retrieval_ms' in breakdown:
        keys.insert(2, 'retrieval_ms')
    verification = result.get('verification_result') or {}
    supported, unsupported = _claims(verification)
    confidence = result.get('confidence_score') or {}
    message = (ChatMessage.objects.filter(session__user=request.user, metadata__model_info__reasoning_session_id=str(s.session_id))
               .select_related('session').first())
    chunks = s.chunks.order_by('-similarity_score')
    return Response({
        'session_id': str(s.session_id), 'created_at': s.created_at, 'question': s.original_query,
        'rewritten_query': s.rewritten_query, 'follow_up': _is_follow_up(s), 'category': s.classification_category, 'pipeline': s.pipeline_name,
        'subject': Subject.objects.filter(id=s.subject_id).values('id', 'name').first(),
        'chat': {'subject_id': message.session.subject_id, 'session_id': message.session_id} if message else None,
        'total_ms': total,
        'stages': [{'name': k.removesuffix('_ms').replace('_', ' '), 'ms': breakdown[k],
                    'pct': round(100 * breakdown[k] / total, 1) if total else 0} for k in keys],
        'chunks': [_chunk(c) for c in chunks if not c.used_in_retry],
        'retry_chunks': [_chunk(c) for c in chunks if c.used_in_retry],
        'prompts': result.get('prompts') or {},
        'generated_answer': s.generated_answer, 'final_answer': s.final_answer, 'retry_count': s.retry_count,
        'retries': result.get('retry_results') or [],
        'verification': {'grounded': verification.get('grounded'), 'reasoning': verification.get('reasoning', ''),
                         'supported_claims': supported, 'unsupported_claims': unsupported},
        'unverified': s.unverified,
        'confidence': {'score': confidence.get('final_score', s.confidence_score),
                       'interpretation': confidence.get('interpretation', s.confidence_interpretation),
                       'breakdown': confidence.get('score_breakdown') or {}},
        'evaluations': [
            {'evaluator': e.evaluator, 'faithfulness': e.faithfulness, 'hallucination_rate': e.hallucination_rate,
             'retrieval_mean_similarity': e.retrieval_mean_similarity, 'retrieval_top_similarity': e.retrieval_top_similarity,
             'answer_relevance': e.answer_relevance, 'reasoning': e.reasoning, 'created_at': e.created_at}
            for e in s.evaluations.all()
        ],
    })
