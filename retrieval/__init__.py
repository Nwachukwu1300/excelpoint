"""
Retrieval System Optimization module for ExcelPoint.

This Django app provides advanced retrieval capabilities including:
- Multiple chunking strategies (fixed-size, overlap-based, semantic)
- Multiple embedding model support (OpenAI, SentenceTransformers)
- Reranking capabilities (cross-encoder, keyword overlap)
- Configurable retrieval pipelines
- Metrics tracking for all retrieval operations
- Experiment storage and comparison for A/B testing

Stage 1 of the ExcelPoint AI platform evolution.
"""

default_app_config = 'retrieval.apps.RetrievalConfig'
