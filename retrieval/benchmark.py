"""
Offline retrieval benchmark: hit@k and MRR over a labelled question set.

A case is {"subject_id": int, "question": str, "expected": str | [str]}. A retrieved
chunk counts as relevant if it contains any expected snippet (case-insensitive), so
cases survive re-chunking, unlike chunk ids.
"""

from statistics import mean


def first_relevant_rank(chunks, expected):
    snippets = [e.lower() for e in ([expected] if isinstance(expected, str) else expected)]
    for rank, chunk in enumerate(chunks, 1):
        if any(s in chunk.content.lower() for s in snippets):
            return rank
    return None


def run_benchmark(cases, pipeline):
    """Run every case through a RetrievalPipeline; returns (per-case rows, summary)."""
    rows = []
    for case in cases:
        result = pipeline.search(query=case['question'], subject_id=case['subject_id'])
        rank = first_relevant_rank(result.chunks, case['expected'])
        rows.append({
            'question': case['question'],
            'subject_id': case['subject_id'],
            'rank': rank,
            'hit': rank is not None,
            'top_score': result.chunks[0].initial_score if result.chunks else None,
            'latency_ms': result.total_latency_ms,
            'retrieved': [{'chunk_id': c.chunk_id, 'score': c.initial_score} for c in result.chunks],
        })
    summary = {
        'cases': len(rows),
        f'hit_at_{pipeline.config.top_k}': mean(r['hit'] for r in rows) if rows else None,
        'mrr': mean(1 / r['rank'] if r['rank'] else 0 for r in rows) if rows else None,
        'mean_latency_ms': mean(r['latency_ms'] for r in rows) if rows else None,
    }
    return rows, summary
