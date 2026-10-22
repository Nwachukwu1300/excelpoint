"""
Metrics collection module for retrieval operations.

This module provides utilities for tracking and recording performance
metrics for retrieval operations. Metrics are persisted to the database
for analysis and comparison.

Tracked metrics:
- Pipeline configuration name
- Query text
- Top-K setting
- Retrieved chunk count and scores
- Latency breakdown (embedding, search, reranking, total)
- Reranking status

Usage:
    from retrieval.metrics import MetricsCollector

    MetricsCollector().record_retrieval(
        pipeline_name='my_pipeline', query='What is AI?', chunks=result.chunks,
        top_k=5, reranking_applied=False, total_latency_ms=result.total_latency_ms,
    )
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from django.db.models import Avg, Max, Min, Count, F
from django.utils import timezone

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collector for retrieval operation metrics.

    Records a retrieval operation's scores and latencies to the database.
    """

    def record_retrieval(
        self,
        pipeline_name: str,
        query: str,
        chunks: List[Any],
        top_k: int,
        reranking_applied: bool,
        reranker_used: Optional[str] = None,
        total_latency_ms: Optional[float] = None,
        embedding_latency_ms: Optional[float] = None,
        search_latency_ms: Optional[float] = None,
        reranking_latency_ms: Optional[float] = None
    ) -> 'RetrievalMetric':
        """
        Record a retrieval operation to the database.

        Args:
            pipeline_name: The name of the pipeline used.
            query: The search query.
            chunks: List of retrieved chunks (must have initial_score or reranked_score).
            top_k: The top-K setting used.
            reranking_applied: Whether reranking was applied.
            reranker_used: The reranker name if reranking was applied.
            total_latency_ms: Total operation latency (0 if not provided).
            embedding_latency_ms: Embedding latency (0 if not provided).
            search_latency_ms: Search latency (0 if not provided).
            reranking_latency_ms: Reranking latency, if reranking ran.

        Returns:
            The created RetrievalMetric instance.
        """
        from .models import RetrievalMetric

        # Calculate scores from chunks
        if chunks:
            # Cosine similarity only: reranker scores are unbounded logits, not similarities
            scores = []
            for chunk in chunks:
                if hasattr(chunk, 'initial_score'):
                    scores.append(chunk.initial_score)
                elif isinstance(chunk, dict):
                    scores.append(chunk.get('initial_score', chunk.get('similarity_score', 0)))

            mean_score = sum(scores) / len(scores) if scores else 0.0
            top_score = max(scores) if scores else 0.0
        else:
            mean_score = 0.0
            top_score = 0.0

        total_latency_ms = total_latency_ms or 0.0
        embedding_latency_ms = embedding_latency_ms or 0.0
        search_latency_ms = search_latency_ms or 0.0

        metric = RetrievalMetric(
            pipeline_name=pipeline_name,
            query=query,
            top_k=top_k,
            retrieved_chunk_count=len(chunks),
            mean_similarity_score=mean_score,
            top_score=top_score,
            reranking_applied=reranking_applied,
            reranker_used=reranker_used,
            total_latency_ms=total_latency_ms,
            embedding_latency_ms=embedding_latency_ms,
            search_latency_ms=search_latency_ms,
            reranking_latency_ms=reranking_latency_ms
        )
        metric.save()

        logger.info(
            f"Recorded retrieval metric for pipeline '{pipeline_name}': "
            f"{len(chunks)} chunks, mean_score={mean_score:.4f}, "
            f"latency={total_latency_ms:.2f}ms"
        )

        return metric


class MetricsAnalyzer:
    """
    Analyzer for retrieval metrics.

    Provides methods to query and analyze stored retrieval metrics,
    including aggregations, comparisons, and trend analysis.
    """

    @staticmethod
    def get_metrics(
        pipeline_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get retrieval metrics with optional filtering.

        Args:
            pipeline_name: Filter by pipeline name.
            start_date: Filter by start date (inclusive).
            end_date: Filter by end date (inclusive).
            limit: Maximum number of results.

        Returns:
            A list of metric dictionaries.
        """
        from .models import RetrievalMetric

        queryset = RetrievalMetric.objects.all()

        if pipeline_name:
            queryset = queryset.filter(pipeline_name=pipeline_name)

        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)

        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        queryset = queryset.order_by('-created_at')[:limit]

        return [
            {
                'id': m.id,
                'pipeline_name': m.pipeline_name,
                'query': m.query,
                'top_k': m.top_k,
                'retrieved_chunk_count': m.retrieved_chunk_count,
                'mean_similarity_score': m.mean_similarity_score,
                'top_score': m.top_score,
                'reranking_applied': m.reranking_applied,
                'reranker_used': m.reranker_used,
                'total_latency_ms': m.total_latency_ms,
                'embedding_latency_ms': m.embedding_latency_ms,
                'search_latency_ms': m.search_latency_ms,
                'reranking_latency_ms': m.reranking_latency_ms,
                'created_at': m.created_at.isoformat(),
            }
            for m in queryset
        ]

    @staticmethod
    def get_pipeline_stats(pipeline_name: str) -> Dict[str, Any]:
        """
        Get aggregated statistics for a pipeline.

        Args:
            pipeline_name: The pipeline name.

        Returns:
            A dictionary containing aggregated statistics.
        """
        from .models import RetrievalMetric

        queryset = RetrievalMetric.objects.filter(pipeline_name=pipeline_name)

        if not queryset.exists():
            return {
                'pipeline_name': pipeline_name,
                'total_queries': 0,
                'message': 'No metrics found for this pipeline'
            }

        stats = queryset.aggregate(
            total_queries=Count('id'),
            avg_latency=Avg('total_latency_ms'),
            max_latency=Max('total_latency_ms'),
            min_latency=Min('total_latency_ms'),
            avg_embedding_latency=Avg('embedding_latency_ms'),
            avg_search_latency=Avg('search_latency_ms'),
            avg_reranking_latency=Avg('reranking_latency_ms'),
            avg_chunk_count=Avg('retrieved_chunk_count'),
            avg_mean_score=Avg('mean_similarity_score'),
            avg_top_score=Avg('top_score'),
            reranking_count=Count('id', filter=F('reranking_applied'))
        )

        return {
            'pipeline_name': pipeline_name,
            'total_queries': stats['total_queries'],
            'avg_total_latency_ms': stats['avg_latency'],
            'max_total_latency_ms': stats['max_latency'],
            'min_total_latency_ms': stats['min_latency'],
            'avg_embedding_latency_ms': stats['avg_embedding_latency'],
            'avg_search_latency_ms': stats['avg_search_latency'],
            'avg_reranking_latency_ms': stats['avg_reranking_latency'],
            'avg_chunk_count': stats['avg_chunk_count'],
            'avg_mean_score': stats['avg_mean_score'],
            'avg_top_score': stats['avg_top_score'],
            'queries_with_reranking': stats['reranking_count'],
            'reranking_rate': (
                stats['reranking_count'] / stats['total_queries']
                if stats['total_queries'] > 0 else 0
            )
        }

    @staticmethod
    def compare_pipelines(
        pipeline_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare statistics across multiple pipelines.

        Args:
            pipeline_names: List of pipeline names to compare.

        Returns:
            A dictionary mapping pipeline names to their statistics.
        """
        comparison = {}
        for name in pipeline_names:
            comparison[name] = MetricsAnalyzer.get_pipeline_stats(name)
        return comparison

    @staticmethod
    def get_latency_breakdown(
        pipeline_name: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get latency breakdown over a time period.

        Args:
            pipeline_name: Optional pipeline name filter.
            days: Number of days to analyze.

        Returns:
            A dictionary containing latency breakdown.
        """
        from .models import RetrievalMetric

        start_date = timezone.now() - timedelta(days=days)
        queryset = RetrievalMetric.objects.filter(created_at__gte=start_date)

        if pipeline_name:
            queryset = queryset.filter(pipeline_name=pipeline_name)

        if not queryset.exists():
            return {
                'period_days': days,
                'pipeline_name': pipeline_name,
                'total_queries': 0,
                'message': 'No metrics found for this period'
            }

        stats = queryset.aggregate(
            total_queries=Count('id'),
            total_latency_avg=Avg('total_latency_ms'),
            embedding_latency_avg=Avg('embedding_latency_ms'),
            search_latency_avg=Avg('search_latency_ms'),
            reranking_latency_avg=Avg('reranking_latency_ms')
        )

        # Calculate percentage breakdown
        total = stats['total_latency_avg'] or 1
        embedding_pct = (stats['embedding_latency_avg'] or 0) / total * 100
        search_pct = (stats['search_latency_avg'] or 0) / total * 100
        reranking_pct = (stats['reranking_latency_avg'] or 0) / total * 100
        other_pct = 100 - embedding_pct - search_pct - reranking_pct

        return {
            'period_days': days,
            'pipeline_name': pipeline_name,
            'total_queries': stats['total_queries'],
            'avg_total_latency_ms': stats['total_latency_avg'],
            'breakdown': {
                'embedding': {
                    'avg_ms': stats['embedding_latency_avg'],
                    'percentage': embedding_pct
                },
                'search': {
                    'avg_ms': stats['search_latency_avg'],
                    'percentage': search_pct
                },
                'reranking': {
                    'avg_ms': stats['reranking_latency_avg'],
                    'percentage': reranking_pct
                },
                'other': {
                    'percentage': max(0, other_pct)
                }
            }
        }
