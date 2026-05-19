"""
URL patterns for the retrieval system API.

This module defines all URL routes for the retrieval optimization API.

Endpoints:
    Pipelines:
        POST /api/retrieval/pipelines/ - Create a pipeline configuration
        GET /api/retrieval/pipelines/ - List all pipeline configurations
        GET /api/retrieval/pipelines/<name>/ - Get pipeline details
        DELETE /api/retrieval/pipelines/<name>/ - Delete a pipeline

    Query:
        POST /api/retrieval/query/ - Run a query through a pipeline

    Experiments:
        POST /api/retrieval/experiments/ - Create an experiment
        GET /api/retrieval/experiments/ - List all experiments
        GET /api/retrieval/experiments/<name>/ - Get experiment details
        DELETE /api/retrieval/experiments/<name>/ - Delete an experiment
        POST /api/retrieval/experiments/run/ - Run an experiment
        GET /api/retrieval/experiments/compare/ - Compare two experiments

    Metrics:
        GET /api/retrieval/metrics/ - List retrieval metrics
        GET /api/retrieval/metrics/stats/<pipeline_name>/ - Get pipeline stats
        GET /api/retrieval/metrics/latency/ - Get latency breakdown

    Info:
        GET /api/retrieval/strategies/ - List available strategies and models
"""

from django.urls import path

from .views import (
    PipelineListCreateView,
    PipelineDetailView,
    QueryView,
    ExperimentListCreateView,
    ExperimentDetailView,
    ExperimentRunView,
    ExperimentCompareView,
    MetricsListView,
    MetricsStatsView,
    MetricsLatencyBreakdownView,
    StrategiesView
)

app_name = 'retrieval'

urlpatterns = [
    # Pipeline endpoints
    path(
        'pipelines/',
        PipelineListCreateView.as_view(),
        name='pipeline-list-create'
    ),
    path(
        'pipelines/<str:name>/',
        PipelineDetailView.as_view(),
        name='pipeline-detail'
    ),

    # Query endpoint
    path(
        'query/',
        QueryView.as_view(),
        name='query'
    ),

    # Experiment endpoints
    path(
        'experiments/',
        ExperimentListCreateView.as_view(),
        name='experiment-list-create'
    ),
    path(
        'experiments/run/',
        ExperimentRunView.as_view(),
        name='experiment-run'
    ),
    path(
        'experiments/compare/',
        ExperimentCompareView.as_view(),
        name='experiment-compare'
    ),
    path(
        'experiments/<str:name>/',
        ExperimentDetailView.as_view(),
        name='experiment-detail'
    ),

    # Metrics endpoints
    path(
        'metrics/',
        MetricsListView.as_view(),
        name='metrics-list'
    ),
    path(
        'metrics/stats/<str:pipeline_name>/',
        MetricsStatsView.as_view(),
        name='metrics-stats'
    ),
    path(
        'metrics/latency/',
        MetricsLatencyBreakdownView.as_view(),
        name='metrics-latency'
    ),

    # Info endpoint
    path(
        'strategies/',
        StrategiesView.as_view(),
        name='strategies'
    ),
]
