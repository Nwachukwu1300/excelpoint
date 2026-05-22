"""
Stage 2: Agentic Reasoning Pipeline

This Django app provides intelligent query classification, query rewriting,
multi-step retrieval and reasoning, answer verification, retry mechanisms,
and confidence scoring for the ExcelPoint learning platform.

Components:
- QueryClassifier: Classifies queries to determine processing path
- QueryRewriter: Rewrites queries for improved retrieval
- AnswerVerifier: Verifies answers are grounded in retrieved content
- ConfidenceScorer: Calculates confidence scores for responses
- RetryHandler: Handles retry logic when verification fails
- ReasoningPipeline: Orchestrates the full reasoning flow

Usage:
    from reasoning.pipeline import ReasoningPipeline

    pipeline = ReasoningPipeline()
    result = pipeline.run(
        query="What is machine learning?",
        subject_id=1,
        conversation_history=None,
        pipeline_name="default"
    )
"""

default_app_config = 'reasoning.apps.ReasoningConfig'
