"""Django app configuration for the subjects application.

This module configures the subjects Django app, which provides the core
functionality for managing educational content, materials, and AI-powered
chat sessions. The app handles file uploads, content processing, vector
search, and RAG-based chatbot interactions.

Key responsibilities:
- Subject and material management
- Content chunking and vector embeddings
- Quiz and flashcard generation
- AI chatbot session management
- File storage abstraction
"""

from django.apps import AppConfig


class SubjectsConfig(AppConfig):
    """Configuration class for the subjects Django application.
    
    This class defines the app's metadata and configuration options.
    It uses Django's default auto field configuration for model IDs.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'subjects'
