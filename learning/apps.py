"""Django app configuration for the learning application.

This module configures the learning Django app, which provides functionality
for tracking user learning progress, managing external courses, and handling
learning resources. Initial courses and achievements are loaded by migration
0006_load_initial_data.

Key responsibilities:
- Course progress tracking and management
- Learning resource discovery and organization
- Achievement and milestone tracking
- External course integration
- Learning path recommendations
"""

from django.apps import AppConfig


class LearningConfig(AppConfig):
    """Configuration class for the learning Django application.
    
    This class defines the app's metadata and configuration options.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'learning'

