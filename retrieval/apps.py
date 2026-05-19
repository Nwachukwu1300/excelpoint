"""Django app configuration for the retrieval module."""

from django.apps import AppConfig


class RetrievalConfig(AppConfig):
    """
    Configuration for the retrieval optimization app.

    This app provides Stage 1 functionality for the ExcelPoint platform:
    - Multiple chunking strategies
    - Multiple embedding model support
    - Reranking capabilities
    - Configurable retrieval pipelines
    - Metrics tracking
    - Experiment storage and comparison
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'retrieval'
    verbose_name = 'Retrieval System Optimization'
