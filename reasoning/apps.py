"""
Django app configuration for the reasoning pipeline.
"""

from django.apps import AppConfig


class ReasoningConfig(AppConfig):
    """
    Configuration for the Stage 2 Agentic Reasoning Pipeline app.

    This app provides intelligent query classification, query rewriting,
    multi-step reasoning, answer verification, and confidence scoring.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reasoning'
    verbose_name = 'Stage 2: Agentic Reasoning Pipeline'

    def ready(self):
        """
        Called when the app is ready.

        Can be used to register signals or perform other initialization.
        """
        pass
