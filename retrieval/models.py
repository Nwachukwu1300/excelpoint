"""
Django models for the retrieval system.

This module defines the database models for storing retrieval pipeline
configurations, metrics, experiments, and experiment results.

Models:
- RetrievalPipelineConfig: Named pipeline configurations
- RetrievalMetric: Per-query retrieval metrics
- RetrievalExperiment: Named experiment definitions
- RetrievalExperimentResult: Results from running experiments
"""

from django.db import models
from django.utils import timezone


class RetrievalPipelineConfig(models.Model):
    """
    Stores named retrieval pipeline configurations.

    Pipeline configurations define all parameters needed to run a retrieval
    pipeline, including embedding model, chunking strategy, and reranking.

    Attributes:
        name: Unique identifier for this configuration.
        description: Human-readable description.
        config: JSON field containing the full configuration.
        created_at: When the configuration was created.
        updated_at: When the configuration was last updated.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique name for this pipeline configuration"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Human-readable description of this pipeline"
    )
    config = models.JSONField(
        help_text="Full pipeline configuration as JSON"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this configuration was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this configuration was last updated"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Retrieval Pipeline Configuration'
        verbose_name_plural = 'Retrieval Pipeline Configurations'

    def __str__(self) -> str:
        return f"Pipeline: {self.name}"

    def get_config_summary(self) -> dict:
        """
        Get a summary of the configuration.

        Returns:
            A dictionary with key configuration values.
        """
        return {
            'name': self.name,
            'embedding_model': self.config.get('embedding_model', 'N/A'),
            'chunking_strategy': self.config.get('chunking_strategy', 'N/A'),
            'top_k': self.config.get('top_k', 'N/A'),
            'reranking_enabled': self.config.get('reranking_enabled', False),
        }


class RetrievalMetric(models.Model):
    """
    Stores metrics for individual retrieval operations.

    Each record represents one query execution through a retrieval pipeline,
    capturing timing, scoring, and configuration information.

    Attributes:
        pipeline_name: The pipeline configuration used.
        query: The search query.
        top_k: The top-K setting used.
        retrieved_chunk_count: Number of chunks returned.
        mean_similarity_score: Average similarity score of results.
        top_score: Highest similarity score.
        reranking_applied: Whether reranking was used.
        reranker_used: The reranker name if reranking was applied.
        total_latency_ms: Total execution time.
        embedding_latency_ms: Time spent on query embedding.
        search_latency_ms: Time spent on vector search.
        reranking_latency_ms: Time spent on reranking.
        created_at: When this metric was recorded.
    """

    pipeline_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Name of the pipeline configuration used"
    )
    query = models.TextField(
        help_text="The search query"
    )
    top_k = models.IntegerField(
        help_text="The top-K setting used for retrieval"
    )
    retrieved_chunk_count = models.IntegerField(
        help_text="Number of chunks retrieved"
    )
    mean_similarity_score = models.FloatField(
        help_text="Average similarity score of retrieved chunks"
    )
    top_score = models.FloatField(
        help_text="Highest similarity score among retrieved chunks"
    )
    reranking_applied = models.BooleanField(
        default=False,
        help_text="Whether reranking was applied"
    )
    reranker_used = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="The reranker used if reranking was applied"
    )
    total_latency_ms = models.FloatField(
        help_text="Total execution time in milliseconds"
    )
    embedding_latency_ms = models.FloatField(
        help_text="Time spent on query embedding in milliseconds"
    )
    search_latency_ms = models.FloatField(
        help_text="Time spent on vector search in milliseconds"
    )
    reranking_latency_ms = models.FloatField(
        null=True,
        blank=True,
        help_text="Time spent on reranking in milliseconds"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this metric was recorded"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Retrieval Metric'
        verbose_name_plural = 'Retrieval Metrics'
        indexes = [
            models.Index(fields=['pipeline_name', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f"Metric: {self.pipeline_name} @ {self.created_at}"

    def get_latency_breakdown(self) -> dict:
        """
        Get a breakdown of latency by stage.

        Returns:
            A dictionary mapping stage names to latencies.
        """
        breakdown = {
            'embedding_ms': self.embedding_latency_ms,
            'search_ms': self.search_latency_ms,
            'total_ms': self.total_latency_ms,
        }
        if self.reranking_latency_ms is not None:
            breakdown['reranking_ms'] = self.reranking_latency_ms
        return breakdown


class RetrievalExperiment(models.Model):
    """
    Stores named experiment configurations for A/B testing retrieval.

    An experiment defines a specific pipeline configuration to test,
    along with metadata for tracking and comparison.

    Attributes:
        name: Unique name for this experiment.
        description: Human-readable description.
        pipeline_config: JSON field containing the pipeline configuration.
        notes: Additional notes about the experiment.
        created_at: When the experiment was created.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique name for this experiment"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Description of what this experiment tests"
    )
    pipeline_config = models.JSONField(
        help_text="Pipeline configuration for this experiment"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Additional notes about this experiment"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this experiment was created"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Retrieval Experiment'
        verbose_name_plural = 'Retrieval Experiments'

    def __str__(self) -> str:
        return f"Experiment: {self.name}"

    def get_result_count(self) -> int:
        """
        Get the number of results for this experiment.

        Returns:
            The count of experiment results.
        """
        return self.results.count()


class RetrievalExperimentResult(models.Model):
    """
    Stores results from running an experiment.

    Each result represents one query execution during an experiment,
    capturing the retrieved chunks and metrics.

    Attributes:
        experiment: Foreign key to the parent experiment.
        query: The search query used.
        subject_id: The subject ID that was searched.
        results: JSON field containing retrieved chunks.
        metrics: JSON field containing timing and scoring metrics.
        created_at: When this result was recorded.
    """

    experiment = models.ForeignKey(
        RetrievalExperiment,
        on_delete=models.CASCADE,
        related_name='results',
        help_text="The experiment this result belongs to"
    )
    query = models.TextField(
        help_text="The search query used"
    )
    subject_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="The subject ID that was searched"
    )
    results = models.JSONField(
        help_text="Retrieved chunks as JSON"
    )
    metrics = models.JSONField(
        help_text="Timing and scoring metrics as JSON"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this result was recorded"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Retrieval Experiment Result'
        verbose_name_plural = 'Retrieval Experiment Results'
        indexes = [
            models.Index(fields=['experiment', 'created_at']),
        ]

    def __str__(self) -> str:
        return f"Result: {self.experiment.name} - {self.query[:50]}"

    def get_chunk_count(self) -> int:
        """
        Get the number of chunks in the results.

        Returns:
            The count of retrieved chunks.
        """
        if isinstance(self.results, list):
            return len(self.results)
        return 0

    def get_metrics_summary(self) -> dict:
        """
        Get a summary of the metrics.

        Returns:
            A dictionary with key metrics.
        """
        return {
            'total_latency_ms': self.metrics.get('total_latency_ms'),
            'chunk_count': self.metrics.get('chunk_count'),
            'mean_score': self.metrics.get('mean_score'),
            'top_score': self.metrics.get('top_score'),
            'reranking_applied': self.metrics.get('reranking_applied', False),
        }
