"""
Stage 3 answer evaluation.

Heuristic metrics come free from data the pipeline already produced (verifier claims,
retrieval scores), so every session gets them. The LLM judge is optional and runs async.
"""

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
