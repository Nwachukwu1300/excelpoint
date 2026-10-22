"""
Stage 3 answer evaluation.

Heuristic metrics come free from data the pipeline already produced (verifier claims,
retrieval scores), so every session gets them. The LLM judge is optional and runs async.
"""

import json
from datetime import timedelta
from statistics import mean

from django.db.models import Avg, Count, FloatField, Q
from django.db.models.fields.json import KT
from django.db.models.functions import Cast, TruncDate
from django.utils import timezone

from .models import AnswerEvaluation


def heuristic_metrics(result):
    """Faithfulness, hallucination rate and retrieval similarity for a ReasoningResult."""
    verification = result.verification_result
    chunks = result.final_chunks or result.retrieved_chunks  # the chunks behind the final answer
    scores = [c.initial_score for c in chunks]
    hallucination_rate = None
    faithfulness = None
    if verification is not None and chunks:
        faithfulness = verification.faithfulness_score
        claims = len(verification.supported_claims) + len(verification.unsupported_claims)
        if claims:
            hallucination_rate = len(verification.unsupported_claims) / claims
    return {
        'faithfulness': faithfulness,
        'hallucination_rate': hallucination_rate,
        'retrieval_mean_similarity': mean(scores) if scores else None,
        'retrieval_top_similarity': max(scores) if scores else None,
    }


def record_heuristic_evaluation(session, result):
    return AnswerEvaluation.objects.create(session=session, evaluator='heuristic', **heuristic_metrics(result))


JUDGE_PROMPT = """You are grading a study assistant that must answer ONLY from the user's uploaded materials.

QUESTION:
{question}

RETRIEVED MATERIALS:
{context}

ANSWER:
{answer}

Return JSON with:
- "answer_relevance": 0-1, how directly and completely the answer addresses the question
- "faithfulness": 0-1, the share of the answer's claims supported by the materials
- "unsupported_claims": list of claims not found in the materials
- "reasoning": one or two sentences explaining the scores"""


def _clamp(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def judge_session(session, client=None):
    """Score a saved session with an LLM judge and store it as an 'llm_judge' evaluation."""
    from django.conf import settings
    from openai import OpenAI

    client = client or OpenAI(api_key=settings.OPENAI_API_KEY)
    # Grade against the chunks behind the final answer (a retry's, if one won), each chunk once
    final_ids = (session.full_result or {}).get('final_chunk_ids')
    rows = session.chunks.filter(chunk_id__in=final_ids) if final_ids else session.chunks.filter(used_in_retry=False)
    chunks = {c.chunk_id: c for c in rows}.values()
    context = "\n\n---\n\n".join(
        f"[{c.material_name}]\n{c.chunk_text[:1500]}" for c in chunks
    ) or "(nothing retrieved)"
    response = client.chat.completions.create(
        model=settings.EVAL_JUDGE_MODEL,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            question=session.original_query, context=context, answer=session.final_answer)}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content or "{}")
    claims = data.get("unsupported_claims") or []
    return AnswerEvaluation.objects.create(
        session=session,
        evaluator='llm_judge',
        answer_relevance=_clamp(data.get("answer_relevance")),
        faithfulness=_clamp(data.get("faithfulness")),
        reasoning=str(data.get("reasoning", ""))[:2000] + (f"\nUnsupported: {claims}" if claims else ""),
    )


def _avg(field, evaluator):
    return Avg(f'evaluations__{field}', filter=Q(evaluations__evaluator=evaluator))


def quality_summary(sessions, days=30, failure_limit=20):
    """Dashboard data for a queryset of ReasoningSessions: totals, daily trends, failures, retrieval."""
    sessions = sessions.filter(created_at__gte=timezone.now() - timedelta(days=days))
    answered = Q(retrieved_chunk_count__gt=0)
    metrics = dict(
        sessions=Count('id', distinct=True),
        no_context=Count('id', filter=~answered, distinct=True),
        unverified=Count('id', filter=answered & Q(unverified=True), distinct=True),
        faithfulness=_avg('faithfulness', 'heuristic'),
        hallucination_rate=_avg('hallucination_rate', 'heuristic'),
        retrieval_top_similarity=_avg('retrieval_top_similarity', 'heuristic'),
        judge_relevance=_avg('answer_relevance', 'llm_judge'),
        judge_faithfulness=_avg('faithfulness', 'llm_judge'),
    )

    totals = sessions.aggregate(**metrics)
    trends = list(
        sessions.annotate(day=TruncDate('created_at')).values('day').annotate(**metrics).order_by('day')
    )

    retrieval = sessions.aggregate(
        avg_chunks=Avg('retrieved_chunk_count'),
        avg_retrieval_ms=Avg(Cast(KT('latency_breakdown__retrieval_ms'), FloatField())),
        avg_total_ms=Avg('total_latency'),
    )
    retrieval['no_context_rate'] = totals['no_context'] / totals['sessions'] if totals['sessions'] else None
    retrieval['avg_top_similarity'] = totals['retrieval_top_similarity']

    failures = []
    for s in sessions.prefetch_related('evaluations').order_by('-created_at')[:200]:
        evals = {e.evaluator: e for e in s.evaluations.all()}
        reasons = []
        if not s.retrieved_chunk_count:
            reasons.append('nothing retrieved')
        elif s.unverified:
            reasons.append('not verified')
        h = evals.get('heuristic')
        if h and h.hallucination_rate:
            reasons.append(f'{h.hallucination_rate:.0%} unsupported claims')
        j = evals.get('llm_judge')
        if j and j.answer_relevance is not None and j.answer_relevance < 0.5:
            reasons.append(f'low relevance ({j.answer_relevance:.2f})')
        if reasons:
            failures.append({
                'session_id': str(s.session_id),
                'query': s.original_query,
                'reasons': reasons,
                'created_at': s.created_at.isoformat(),
            })
            if len(failures) >= failure_limit:
                break

    return {'days': days, 'totals': totals, 'trends': trends, 'retrieval': retrieval, 'failures': failures}
