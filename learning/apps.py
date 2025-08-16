"""Django app configuration for the learning application.

This module configures the learning Django app, which provides functionality
for tracking user learning progress, managing external courses, and handling
learning resources. The app includes automatic data loading for initial
setup and integrates with the broader learning management system.

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
    It includes automatic data loading for initial setup and ensures
    the database is ready before attempting to load sample data.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'learning'

    def ready(self):
        """Load initial data when the app is ready.
        
        This method is called when Django finishes loading all apps.
        It automatically loads initial learning data (courses, achievements,
        resources) if the database is empty and the environment is ready.
        
        The method includes safety checks to:
        - Avoid running during testing
        - Ensure database connection is established
        - Check if data already exists before loading
        - Gracefully handle startup errors
        """
        import os
        from django.core.management import call_command
        from django.db import connection
        
        # Only run in non-testing environments and when database is ready
        if not os.environ.get('TESTING') and connection.ensure_connection():
            try:
                from learning.models import Course, Achievement, LearningResource
                
                # Check if data already exists
                if not Course.objects.exists() and not Achievement.objects.exists() and not LearningResource.objects.exists():
                    call_command('loaddata', 'initial_data', app_label='learning', verbosity=0)
            except Exception:
                # Ignore errors during startup (database might not be ready yet)
                pass
