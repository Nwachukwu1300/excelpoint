from django.apps import AppConfig


class LearningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'learning'

    def ready(self):
        """Load initial data when the app is ready"""
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
