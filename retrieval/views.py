"""
API views for the retrieval system.

This module provides REST API endpoints for managing retrieval pipelines,
running queries, managing experiments, and viewing metrics.

Endpoints:
- POST/GET /api/retrieval/pipelines/ - Create and list pipeline configurations
- POST /api/retrieval/query/ - Run a query through a pipeline
- POST/GET /api/retrieval/experiments/ - Create and list experiments
- POST /api/retrieval/experiments/run/ - Run an experiment
- GET /api/retrieval/experiments/compare/ - Compare two experiments
- GET /api/retrieval/metrics/ - List retrieval metrics
- GET /api/retrieval/strategies/ - List available strategies and models
"""

from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.utils import timezone
from datetime import datetime
import logging

from .models import (
    RetrievalPipelineConfig,
    RetrievalMetric,
    RetrievalExperiment,
    RetrievalExperimentResult
)
from .serializers import (
    RetrievalPipelineConfigSerializer,
    RetrievalMetricSerializer,
    RetrievalExperimentSerializer,
    RetrievalExperimentResultSerializer,
    PipelineConfigInputSerializer,
    QueryInputSerializer,
    ExperimentInputSerializer,
    ExperimentRunInputSerializer,
    ExperimentCompareInputSerializer,
    MetricsFilterSerializer,
    QueryResultSerializer,
    ExperimentComparisonSerializer,
    PipelineStatsSerializer,
    ChunkingStrategyInfoSerializer,
    EmbeddingModelInfoSerializer,
    RerankerInfoSerializer
)
from .pipeline import RetrievalPipeline, PipelineConfig, PipelineManager
from .experiments import RetrievalExperimentService, ExperimentError
from .metrics import MetricsCollector, MetricsAnalyzer
from .chunking import ChunkingFactory
from .embeddings import EmbeddingFactory, EmbeddingError
from .reranking import RerankerFactory

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Views
# =============================================================================

class PipelineListCreateView(APIView):
    """
    API view for listing and creating pipeline configurations.

    GET: List all saved pipeline configurations.
    POST: Create a new pipeline configuration.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List all pipeline configurations.

        Returns:
            A list of pipeline configuration objects.
        """
        pipelines = RetrievalPipelineConfig.objects.all().order_by('-created_at')
        serializer = RetrievalPipelineConfigSerializer(pipelines, many=True)
        return Response({
            'count': pipelines.count(),
            'results': serializer.data
        })

    def post(self, request):
        """
        Create a new pipeline configuration.

        Request body:
            name: Unique name for the pipeline.
            description: Optional description.
            chunking_strategy: The chunking strategy.
            chunking_params: Parameters for chunking.
            embedding_model: The embedding model.
            top_k: Number of results to retrieve.
            similarity_threshold: Minimum similarity score.
            reranking_enabled: Whether to enable reranking.
            reranker_name: The reranker to use.
            reranker_params: Parameters for the reranker.

        Returns:
            The created pipeline configuration.
        """
        input_serializer = PipelineConfigInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': input_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = input_serializer.validated_data

        # Create the pipeline config
        config = PipelineConfig(
            name=data['name'],
            description=data.get('description', ''),
            chunking_strategy=data.get('chunking_strategy', 'overlap'),
            chunking_params=data.get('chunking_params', {}),
            embedding_model=data.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2'),
            top_k=data.get('top_k', 10),
            similarity_threshold=data.get('similarity_threshold', 0.15),
            reranking_enabled=data.get('reranking_enabled', False),
            reranker_name=data.get('reranker_name', 'cross_encoder'),
            reranker_params=data.get('reranker_params', {})
        )

        try:
            pipeline_model = PipelineManager.create_pipeline(config)
            output_serializer = RetrievalPipelineConfigSerializer(pipeline_model)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to create pipeline: {str(e)}")
            return Response(
                {'error': 'Failed to create pipeline', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PipelineDetailView(APIView):
    """
    API view for retrieving and deleting a specific pipeline configuration.

    GET: Get pipeline details.
    DELETE: Delete a pipeline configuration.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, name):
        """
        Get a pipeline configuration by name.

        Args:
            name: The pipeline name.

        Returns:
            The pipeline configuration details.
        """
        try:
            pipeline = RetrievalPipelineConfig.objects.get(name=name)
            serializer = RetrievalPipelineConfigSerializer(pipeline)
            return Response(serializer.data)
        except RetrievalPipelineConfig.DoesNotExist:
            return Response(
                {'error': f"Pipeline '{name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, name):
        """
        Delete a pipeline configuration.

        Args:
            name: The pipeline name.

        Returns:
            Success message or error.
        """
        if PipelineManager.delete_pipeline(name):
            return Response({'message': f"Pipeline '{name}' deleted"})
        return Response(
            {'error': f"Pipeline '{name}' not found"},
            status=status.HTTP_404_NOT_FOUND
        )


# =============================================================================
# Query View
# =============================================================================

class QueryView(APIView):
    """
    API view for executing queries through a pipeline.

    POST: Run a query through a named pipeline and return results with metrics.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Run a query through a pipeline.

        Request body:
            pipeline_name: Name of the pipeline to use.
            query: The search query.
            subject_id: The subject to search within.

        Returns:
            Retrieved chunks with scores and metrics.
        """
        serializer = QueryInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            # Get the pipeline
            pipeline = PipelineManager.get_pipeline(data['pipeline_name'])

            # Execute the query
            result = pipeline.search(
                query=data['query'],
                subject_id=data['subject_id']
            )

            # Record metrics
            collector = MetricsCollector()
            collector.record_retrieval(
                pipeline_name=data['pipeline_name'],
                query=data['query'],
                chunks=result.chunks,
                top_k=pipeline.config.top_k,
                reranking_applied=result.reranking_applied,
                reranker_used=result.reranker_used,
                total_latency_ms=result.total_latency_ms,
                embedding_latency_ms=result.embedding_latency_ms,
                search_latency_ms=result.search_latency_ms,
                reranking_latency_ms=result.reranking_latency_ms
            )

            # Format response
            response_data = {
                'query': result.query,
                'pipeline_name': result.pipeline_name,
                'chunks': [chunk.to_dict() for chunk in result.chunks],
                'chunk_count': result.chunk_count,
                'mean_score': result.mean_score,
                'top_score': result.top_score,
                'total_latency_ms': result.total_latency_ms,
                'embedding_latency_ms': result.embedding_latency_ms,
                'search_latency_ms': result.search_latency_ms,
                'reranking_latency_ms': result.reranking_latency_ms,
                'reranking_applied': result.reranking_applied,
                'embedding_model': result.embedding_model,
                'reranker_used': result.reranker_used
            }

            return Response(response_data)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except EmbeddingError as e:
            logger.error(f"Embedding error: {str(e)}")
            return Response(
                {'error': 'Embedding failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return Response(
                {'error': 'Query execution failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Experiment Views
# =============================================================================

class ExperimentListCreateView(APIView):
    """
    API view for listing and creating experiments.

    GET: List all experiments.
    POST: Create a new experiment.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List all experiments.

        Returns:
            A list of experiment objects.
        """
        service = RetrievalExperimentService()
        experiments = service.list_experiments()
        return Response({
            'count': len(experiments),
            'results': experiments
        })

    def post(self, request):
        """
        Create a new experiment.

        Request body:
            name: Unique name for the experiment.
            description: Optional description.
            pipeline_config: Pipeline configuration for the experiment.
            notes: Optional notes.

        Returns:
            The created experiment.
        """
        serializer = ExperimentInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        service = RetrievalExperimentService()

        try:
            experiment = service.create_experiment(
                name=data['name'],
                description=data.get('description', ''),
                pipeline_config=data.get('pipeline_config'),
                notes=data.get('notes', '')
            )
            output_serializer = RetrievalExperimentSerializer(experiment)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except ExperimentError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            return Response(
                {'error': 'Invalid configuration', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ExperimentDetailView(APIView):
    """
    API view for retrieving experiment details and results.

    GET: Get experiment details and results.
    DELETE: Delete an experiment.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, name):
        """
        Get experiment details and results.

        Args:
            name: The experiment name.

        Returns:
            Experiment details with result summaries.
        """
        service = RetrievalExperimentService()

        try:
            experiment = service.get_experiment(name)
            results = service.get_experiment_results(name)
            stats = service.get_experiment_stats(name)

            return Response({
                'experiment': RetrievalExperimentSerializer(experiment).data,
                'stats': stats,
                'results': results
            })
        except ExperimentError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, name):
        """
        Delete an experiment and all its results.

        Args:
            name: The experiment name.

        Returns:
            Success message or error.
        """
        service = RetrievalExperimentService()

        if service.delete_experiment(name):
            return Response({'message': f"Experiment '{name}' deleted"})
        return Response(
            {'error': f"Experiment '{name}' not found"},
            status=status.HTTP_404_NOT_FOUND
        )


class ExperimentRunView(APIView):
    """
    API view for running an experiment.

    POST: Run an experiment with a query.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Run an experiment with a query.

        Request body:
            experiment_name: Name of the experiment to run.
            query: The search query.
            subject_id: The subject to search within.

        Returns:
            The experiment result with metrics.
        """
        serializer = ExperimentRunInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        service = RetrievalExperimentService()

        try:
            result = service.run_experiment(
                experiment_name=data['experiment_name'],
                query=data['query'],
                subject_id=data['subject_id']
            )
            output_serializer = RetrievalExperimentResultSerializer(result)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except ExperimentError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ExperimentCompareView(APIView):
    """
    API view for comparing two experiments.

    GET: Compare two experiments by name.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Compare two experiments side by side.

        Query parameters:
            experiment_1: Name of the first experiment.
            experiment_2: Name of the second experiment.

        Returns:
            Side-by-side comparison of experiment statistics.
        """
        serializer = ExperimentCompareInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        service = RetrievalExperimentService()

        try:
            comparison = service.compare_experiments(
                data['experiment_1'],
                data['experiment_2']
            )
            return Response(comparison)
        except ExperimentError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


# =============================================================================
# Metrics Views
# =============================================================================

class MetricsListView(APIView):
    """
    API view for listing retrieval metrics.

    GET: List metrics with optional filtering.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List retrieval metrics with filtering.

        Query parameters:
            pipeline_name: Filter by pipeline name.
            start_date: Filter by start date.
            end_date: Filter by end date.
            limit: Maximum number of results.

        Returns:
            A list of metric records.
        """
        serializer = MetricsFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid filters', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        metrics = MetricsAnalyzer.get_metrics(
            pipeline_name=data.get('pipeline_name'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            limit=data.get('limit', 100)
        )

        return Response({
            'count': len(metrics),
            'results': metrics
        })


class MetricsStatsView(APIView):
    """
    API view for pipeline statistics.

    GET: Get aggregated statistics for a pipeline.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pipeline_name):
        """
        Get aggregated statistics for a pipeline.

        Args:
            pipeline_name: The pipeline name.

        Returns:
            Aggregated statistics.
        """
        stats = MetricsAnalyzer.get_pipeline_stats(pipeline_name)
        return Response(stats)


class MetricsLatencyBreakdownView(APIView):
    """
    API view for latency breakdown analysis.

    GET: Get latency breakdown for a pipeline or overall.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get latency breakdown.

        Query parameters:
            pipeline_name: Optional pipeline name filter.
            days: Number of days to analyze (default 7).

        Returns:
            Latency breakdown by stage.
        """
        pipeline_name = request.query_params.get('pipeline_name')
        days = int(request.query_params.get('days', 7))

        breakdown = MetricsAnalyzer.get_latency_breakdown(
            pipeline_name=pipeline_name,
            days=days
        )
        return Response(breakdown)


# =============================================================================
# Strategy Info Views
# =============================================================================

class StrategiesView(APIView):
    """
    API view for listing available strategies and models.

    GET: List all available chunking strategies, embedding models, and rerankers.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List all available strategies and models.

        Returns:
            Available chunking strategies, embedding models, and rerankers.
        """
        # Get chunking strategies
        chunking_strategies = []
        for strategy_name in ChunkingFactory.list_strategies():
            try:
                info = ChunkingFactory.get_strategy_info(strategy_name)
                chunking_strategies.append({
                    'name': info['name'],
                    'description': (info['description'] or '').split('\n')[0],
                    'parameters': info['parameters']
                })
            except Exception:
                chunking_strategies.append({'name': strategy_name})

        # Get embedding models
        embedding_models = EmbeddingFactory.list_models()

        # Get rerankers
        rerankers = []
        for reranker_name in RerankerFactory.list_rerankers():
            try:
                info = RerankerFactory.get_reranker_info(reranker_name)
                rerankers.append({
                    'name': info['name'],
                    'description': (info['description'] or '').split('\n')[0],
                    'parameters': info['parameters']
                })
            except Exception:
                rerankers.append({'name': reranker_name})

        return Response({
            'chunking_strategies': chunking_strategies,
            'embedding_models': embedding_models,
            'embedding_aliases': EmbeddingFactory.list_aliases(),
            'rerankers': rerankers
        })
