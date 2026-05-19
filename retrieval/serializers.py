"""
DRF serializers for the retrieval system API.

This module provides serializers for all retrieval models and
request/response payloads. Serializers handle validation, conversion,
and formatting of data for the REST API.

Serializers:
- Model serializers: RetrievalPipelineConfig, RetrievalMetric, etc.
- Request serializers: Pipeline creation, query execution, etc.
- Response serializers: Results, comparisons, etc.
"""

from rest_framework import serializers
from django.utils import timezone

from .models import (
    RetrievalPipelineConfig,
    RetrievalMetric,
    RetrievalExperiment,
    RetrievalExperimentResult
)


# =============================================================================
# Model Serializers
# =============================================================================

class RetrievalPipelineConfigSerializer(serializers.ModelSerializer):
    """
    Serializer for RetrievalPipelineConfig model.

    Handles serialization of pipeline configurations for listing,
    creation, and retrieval operations.
    """

    config_summary = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RetrievalPipelineConfig
        fields = [
            'id',
            'name',
            'description',
            'config',
            'config_summary',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'config_summary']

    def get_config_summary(self, obj) -> dict:
        """Get a summary of the configuration."""
        return obj.get_config_summary()

    def validate_name(self, value: str) -> str:
        """Validate that the name is unique."""
        instance = self.instance
        if RetrievalPipelineConfig.objects.filter(name=value).exclude(
            pk=instance.pk if instance else None
        ).exists():
            raise serializers.ValidationError(
                f"Pipeline configuration with name '{value}' already exists."
            )
        return value

    def validate_config(self, value: dict) -> dict:
        """Validate the pipeline configuration."""
        required_fields = ['embedding_model', 'top_k']
        for field in required_fields:
            if field not in value:
                value[field] = self._get_default(field)

        # Validate top_k
        if value.get('top_k', 0) < 1:
            raise serializers.ValidationError("top_k must be at least 1")

        # Validate similarity_threshold
        threshold = value.get('similarity_threshold', 0.15)
        if not 0 <= threshold <= 1:
            raise serializers.ValidationError(
                "similarity_threshold must be between 0 and 1"
            )

        return value

    def _get_default(self, field: str):
        """Get default value for a config field."""
        defaults = {
            'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2',
            'top_k': 10,
            'similarity_threshold': 0.15,
            'reranking_enabled': False,
            'reranker_name': 'cross_encoder',
            'chunking_strategy': 'overlap',
            'chunking_params': {'chunk_size': 1000, 'overlap_size': 200}
        }
        return defaults.get(field)


class RetrievalMetricSerializer(serializers.ModelSerializer):
    """
    Serializer for RetrievalMetric model.

    Handles serialization of retrieval metrics for listing and filtering.
    """

    latency_breakdown = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RetrievalMetric
        fields = [
            'id',
            'pipeline_name',
            'query',
            'top_k',
            'retrieved_chunk_count',
            'mean_similarity_score',
            'top_score',
            'reranking_applied',
            'reranker_used',
            'total_latency_ms',
            'embedding_latency_ms',
            'search_latency_ms',
            'reranking_latency_ms',
            'latency_breakdown',
            'created_at'
        ]
        read_only_fields = fields

    def get_latency_breakdown(self, obj) -> dict:
        """Get a breakdown of latency by stage."""
        return obj.get_latency_breakdown()


class RetrievalExperimentSerializer(serializers.ModelSerializer):
    """
    Serializer for RetrievalExperiment model.

    Handles serialization of experiment definitions for listing,
    creation, and retrieval operations.
    """

    result_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RetrievalExperiment
        fields = [
            'id',
            'name',
            'description',
            'pipeline_config',
            'notes',
            'result_count',
            'created_at'
        ]
        read_only_fields = ['id', 'result_count', 'created_at']

    def get_result_count(self, obj) -> int:
        """Get the number of results for this experiment."""
        return obj.get_result_count()

    def validate_name(self, value: str) -> str:
        """Validate that the name is unique."""
        instance = self.instance
        if RetrievalExperiment.objects.filter(name=value).exclude(
            pk=instance.pk if instance else None
        ).exists():
            raise serializers.ValidationError(
                f"Experiment with name '{value}' already exists."
            )
        return value


class RetrievalExperimentResultSerializer(serializers.ModelSerializer):
    """
    Serializer for RetrievalExperimentResult model.

    Handles serialization of experiment results for listing and retrieval.
    """

    experiment_name = serializers.CharField(
        source='experiment.name',
        read_only=True
    )
    chunk_count = serializers.SerializerMethodField(read_only=True)
    metrics_summary = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RetrievalExperimentResult
        fields = [
            'id',
            'experiment',
            'experiment_name',
            'query',
            'subject_id',
            'results',
            'metrics',
            'chunk_count',
            'metrics_summary',
            'created_at'
        ]
        read_only_fields = fields

    def get_chunk_count(self, obj) -> int:
        """Get the number of chunks in the results."""
        return obj.get_chunk_count()

    def get_metrics_summary(self, obj) -> dict:
        """Get a summary of the metrics."""
        return obj.get_metrics_summary()


# =============================================================================
# Request Serializers
# =============================================================================

class PipelineConfigInputSerializer(serializers.Serializer):
    """
    Serializer for pipeline configuration input.

    Used when creating or updating pipeline configurations via the API.
    """

    name = serializers.CharField(
        max_length=255,
        help_text="Unique name for this pipeline configuration"
    )
    description = serializers.CharField(
        required=False,
        default='',
        allow_blank=True,
        help_text="Human-readable description"
    )
    chunking_strategy = serializers.ChoiceField(
        choices=['fixed_size', 'overlap', 'semantic'],
        required=False,
        default='overlap',
        help_text="The chunking strategy to use"
    )
    chunking_params = serializers.DictField(
        required=False,
        default={'chunk_size': 1000, 'overlap_size': 200},
        help_text="Parameters for the chunking strategy"
    )
    embedding_model = serializers.CharField(
        required=False,
        default='sentence-transformers/all-MiniLM-L6-v2',
        help_text="The embedding model to use"
    )
    top_k = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=100,
        help_text="Number of results to retrieve"
    )
    similarity_threshold = serializers.FloatField(
        required=False,
        default=0.15,
        min_value=0,
        max_value=1,
        help_text="Minimum similarity score for results"
    )
    reranking_enabled = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether to apply reranking"
    )
    reranker_name = serializers.ChoiceField(
        choices=['cross_encoder', 'keyword_overlap'],
        required=False,
        default='cross_encoder',
        help_text="The reranker to use if reranking is enabled"
    )
    reranker_params = serializers.DictField(
        required=False,
        default={},
        help_text="Parameters for the reranker"
    )

    def validate_name(self, value: str) -> str:
        """Validate that the name is unique."""
        if RetrievalPipelineConfig.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"Pipeline configuration with name '{value}' already exists."
            )
        return value


class QueryInputSerializer(serializers.Serializer):
    """
    Serializer for query execution input.

    Used when running a query through a pipeline.
    """

    pipeline_name = serializers.CharField(
        max_length=255,
        help_text="Name of the pipeline configuration to use"
    )
    query = serializers.CharField(
        min_length=1,
        max_length=5000,
        help_text="The search query"
    )
    subject_id = serializers.IntegerField(
        min_value=1,
        help_text="The subject ID to search within"
    )

    def validate_pipeline_name(self, value: str) -> str:
        """Validate that the pipeline exists."""
        if not RetrievalPipelineConfig.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"Pipeline configuration '{value}' not found."
            )
        return value


class ExperimentInputSerializer(serializers.Serializer):
    """
    Serializer for experiment creation input.

    Used when creating a new experiment.
    """

    name = serializers.CharField(
        max_length=255,
        help_text="Unique name for this experiment"
    )
    description = serializers.CharField(
        required=False,
        default='',
        allow_blank=True,
        help_text="Description of what this experiment tests"
    )
    pipeline_config = serializers.DictField(
        required=False,
        default={},
        help_text="Pipeline configuration for this experiment"
    )
    notes = serializers.CharField(
        required=False,
        default='',
        allow_blank=True,
        help_text="Additional notes"
    )

    def validate_name(self, value: str) -> str:
        """Validate that the name is unique."""
        if RetrievalExperiment.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"Experiment with name '{value}' already exists."
            )
        return value


class ExperimentRunInputSerializer(serializers.Serializer):
    """
    Serializer for experiment run input.

    Used when running an experiment with a query.
    """

    experiment_name = serializers.CharField(
        max_length=255,
        help_text="Name of the experiment to run"
    )
    query = serializers.CharField(
        min_length=1,
        max_length=5000,
        help_text="The search query"
    )
    subject_id = serializers.IntegerField(
        min_value=1,
        help_text="The subject ID to search within"
    )

    def validate_experiment_name(self, value: str) -> str:
        """Validate that the experiment exists."""
        if not RetrievalExperiment.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"Experiment '{value}' not found."
            )
        return value


class ExperimentCompareInputSerializer(serializers.Serializer):
    """
    Serializer for experiment comparison input.

    Used when comparing two experiments.
    """

    experiment_1 = serializers.CharField(
        max_length=255,
        help_text="Name of the first experiment"
    )
    experiment_2 = serializers.CharField(
        max_length=255,
        help_text="Name of the second experiment"
    )

    def validate_experiment_1(self, value: str) -> str:
        """Validate that the experiment exists."""
        if not RetrievalExperiment.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"Experiment '{value}' not found."
            )
        return value

    def validate_experiment_2(self, value: str) -> str:
        """Validate that the experiment exists."""
        if not RetrievalExperiment.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"Experiment '{value}' not found."
            )
        return value


class MetricsFilterSerializer(serializers.Serializer):
    """
    Serializer for metrics filtering input.

    Used when listing metrics with filters.
    """

    pipeline_name = serializers.CharField(
        required=False,
        max_length=255,
        help_text="Filter by pipeline name"
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text="Filter by start date (inclusive)"
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text="Filter by end date (inclusive)"
    )
    limit = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        max_value=1000,
        help_text="Maximum number of results"
    )


# =============================================================================
# Response Serializers
# =============================================================================

class ChunkResultSerializer(serializers.Serializer):
    """
    Serializer for individual chunk results.

    Used in query and experiment result responses.
    """

    chunk_id = serializers.IntegerField()
    content = serializers.CharField()
    chunk_index = serializers.IntegerField()
    material_id = serializers.IntegerField()
    material_name = serializers.CharField()
    initial_score = serializers.FloatField()
    reranked_score = serializers.FloatField(allow_null=True)
    metadata = serializers.DictField(required=False)


class QueryResultSerializer(serializers.Serializer):
    """
    Serializer for query execution results.

    Contains the retrieved chunks and execution metrics.
    """

    query = serializers.CharField()
    pipeline_name = serializers.CharField()
    chunks = ChunkResultSerializer(many=True)
    chunk_count = serializers.IntegerField()
    mean_score = serializers.FloatField()
    top_score = serializers.FloatField()
    total_latency_ms = serializers.FloatField()
    embedding_latency_ms = serializers.FloatField()
    search_latency_ms = serializers.FloatField()
    reranking_latency_ms = serializers.FloatField(allow_null=True)
    reranking_applied = serializers.BooleanField()
    embedding_model = serializers.CharField()
    reranker_used = serializers.CharField(allow_null=True)


class ExperimentComparisonSerializer(serializers.Serializer):
    """
    Serializer for experiment comparison results.

    Contains side-by-side statistics and differences.
    """

    experiment_1 = serializers.DictField()
    experiment_2 = serializers.DictField()
    comparison = serializers.DictField()


class PipelineStatsSerializer(serializers.Serializer):
    """
    Serializer for pipeline statistics.

    Contains aggregated metrics for a pipeline.
    """

    pipeline_name = serializers.CharField()
    total_queries = serializers.IntegerField()
    avg_total_latency_ms = serializers.FloatField(allow_null=True)
    max_total_latency_ms = serializers.FloatField(allow_null=True)
    min_total_latency_ms = serializers.FloatField(allow_null=True)
    avg_embedding_latency_ms = serializers.FloatField(allow_null=True)
    avg_search_latency_ms = serializers.FloatField(allow_null=True)
    avg_reranking_latency_ms = serializers.FloatField(allow_null=True)
    avg_chunk_count = serializers.FloatField(allow_null=True)
    avg_mean_score = serializers.FloatField(allow_null=True)
    avg_top_score = serializers.FloatField(allow_null=True)
    queries_with_reranking = serializers.IntegerField()
    reranking_rate = serializers.FloatField()


class ChunkingStrategyInfoSerializer(serializers.Serializer):
    """
    Serializer for chunking strategy information.
    """

    name = serializers.CharField()
    description = serializers.CharField()
    parameters = serializers.DictField()


class EmbeddingModelInfoSerializer(serializers.Serializer):
    """
    Serializer for embedding model information.
    """

    model_name = serializers.CharField()
    dimensions = serializers.IntegerField()
    provider = serializers.CharField()


class RerankerInfoSerializer(serializers.Serializer):
    """
    Serializer for reranker information.
    """

    name = serializers.CharField()
    description = serializers.CharField()
    parameters = serializers.DictField()
