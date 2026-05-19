"""
Django admin configuration for the retrieval system.

This module registers the retrieval models with Django's admin interface
for easy management and debugging.

Registered models:
- RetrievalPipelineConfig
- RetrievalMetric
- RetrievalExperiment
- RetrievalExperimentResult
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    RetrievalPipelineConfig,
    RetrievalMetric,
    RetrievalExperiment,
    RetrievalExperimentResult
)


@admin.register(RetrievalPipelineConfig)
class RetrievalPipelineConfigAdmin(admin.ModelAdmin):
    """
    Admin configuration for RetrievalPipelineConfig model.

    Displays pipeline configurations with key settings and allows
    searching and filtering.
    """

    list_display = (
        'name',
        'get_embedding_model',
        'get_top_k',
        'get_reranking',
        'created_at',
        'updated_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Configuration', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_embedding_model(self, obj):
        """Display the embedding model from config."""
        return obj.config.get('embedding_model', 'N/A')
    get_embedding_model.short_description = 'Embedding Model'

    def get_top_k(self, obj):
        """Display the top_k from config."""
        return obj.config.get('top_k', 'N/A')
    get_top_k.short_description = 'Top K'

    def get_reranking(self, obj):
        """Display reranking status from config."""
        if obj.config.get('reranking_enabled'):
            return format_html(
                '<span style="color: green;">Enabled ({})</span>',
                obj.config.get('reranker_name', 'N/A')
            )
        return format_html('<span style="color: gray;">Disabled</span>')
    get_reranking.short_description = 'Reranking'


@admin.register(RetrievalMetric)
class RetrievalMetricAdmin(admin.ModelAdmin):
    """
    Admin configuration for RetrievalMetric model.

    Displays metrics with latency and score information,
    allows filtering by pipeline and date.
    """

    list_display = (
        'id',
        'pipeline_name',
        'query_preview',
        'retrieved_chunk_count',
        'top_score_display',
        'total_latency_display',
        'reranking_applied',
        'created_at'
    )
    list_filter = (
        'pipeline_name',
        'reranking_applied',
        'created_at'
    )
    search_fields = ('pipeline_name', 'query')
    readonly_fields = (
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
        'created_at'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Query Info', {
            'fields': ('pipeline_name', 'query', 'top_k')
        }),
        ('Results', {
            'fields': (
                'retrieved_chunk_count',
                'mean_similarity_score',
                'top_score'
            )
        }),
        ('Reranking', {
            'fields': ('reranking_applied', 'reranker_used')
        }),
        ('Latency', {
            'fields': (
                'total_latency_ms',
                'embedding_latency_ms',
                'search_latency_ms',
                'reranking_latency_ms'
            )
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def query_preview(self, obj):
        """Display a truncated query preview."""
        if len(obj.query) > 50:
            return f"{obj.query[:50]}..."
        return obj.query
    query_preview.short_description = 'Query'

    def top_score_display(self, obj):
        """Display top score with color coding."""
        score = obj.top_score
        if score >= 0.8:
            color = 'green'
        elif score >= 0.5:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.4f}</span>',
            color, score
        )
    top_score_display.short_description = 'Top Score'

    def total_latency_display(self, obj):
        """Display total latency with formatting."""
        latency = obj.total_latency_ms
        if latency < 100:
            color = 'green'
        elif latency < 500:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.2f}ms</span>',
            color, latency
        )
    total_latency_display.short_description = 'Latency'


@admin.register(RetrievalExperiment)
class RetrievalExperimentAdmin(admin.ModelAdmin):
    """
    Admin configuration for RetrievalExperiment model.

    Displays experiments with result counts and configuration previews.
    """

    list_display = (
        'name',
        'description_preview',
        'result_count',
        'created_at'
    )
    list_filter = ('created_at',)
    search_fields = ('name', 'description', 'notes')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Configuration', {
            'fields': ('pipeline_config',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def description_preview(self, obj):
        """Display a truncated description preview."""
        if not obj.description:
            return '-'
        if len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description
    description_preview.short_description = 'Description'

    def result_count(self, obj):
        """Display the number of results."""
        count = obj.get_result_count()
        return format_html(
            '<span style="font-weight: bold;">{}</span> results',
            count
        )
    result_count.short_description = 'Results'


@admin.register(RetrievalExperimentResult)
class RetrievalExperimentResultAdmin(admin.ModelAdmin):
    """
    Admin configuration for RetrievalExperimentResult model.

    Displays experiment results with metrics summaries.
    """

    list_display = (
        'id',
        'experiment_name',
        'query_preview',
        'subject_id',
        'chunk_count',
        'latency_display',
        'created_at'
    )
    list_filter = ('experiment', 'created_at')
    search_fields = ('query', 'experiment__name')
    readonly_fields = (
        'experiment',
        'query',
        'subject_id',
        'results',
        'metrics',
        'created_at'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Experiment', {
            'fields': ('experiment', 'query', 'subject_id')
        }),
        ('Results', {
            'fields': ('results',),
            'classes': ('collapse',)
        }),
        ('Metrics', {
            'fields': ('metrics',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def experiment_name(self, obj):
        """Display the experiment name."""
        return obj.experiment.name
    experiment_name.short_description = 'Experiment'

    def query_preview(self, obj):
        """Display a truncated query preview."""
        if len(obj.query) > 50:
            return f"{obj.query[:50]}..."
        return obj.query
    query_preview.short_description = 'Query'

    def chunk_count(self, obj):
        """Display the number of chunks."""
        return obj.get_chunk_count()
    chunk_count.short_description = 'Chunks'

    def latency_display(self, obj):
        """Display latency from metrics."""
        latency = obj.metrics.get('total_latency_ms')
        if latency is None:
            return '-'
        return f"{latency:.2f}ms"
    latency_display.short_description = 'Latency'
