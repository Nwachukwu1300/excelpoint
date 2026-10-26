"""Stage order for answer traces. The Insights pages themselves are now in the React app (reasoning/app_api.py)."""

STAGES = ['classification_ms', 'rewrite_ms', 'embedding_ms', 'search_ms', 'reranking_ms', 'generation_ms', 'verification_ms']
