"""
Stage 3 answer evaluation.

Heuristic metrics come free from data the pipeline already produced (verifier claims,
retrieval scores), so every session gets them. The LLM judge is optional and runs async.
"""

import json
from statistics import mean

from .models import AnswerEvaluation


def heuristic_metrics(result):
    """Faithfulness, hallucination rate and retrieval similarity for a ReasoningResult."""
    verification = result.verification_result
    scores = [c.initial_score for c in result.retrieved_chunks]
    hallucination_rate = None
    faithfulness = None
    if verification is not None and result.retrieved_chunks:
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
    context = "\n\n---\n\n".join(
        f"[{c.material_name}]\n{c.chunk_text[:1500]}" for c in session.chunks.filter(used_in_retry=False)
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
