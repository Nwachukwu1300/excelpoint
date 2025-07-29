from django.core.management.base import BaseCommand
from django.core.management import call_command
from learning.models import Course, Achievement, LearningResource


class Command(BaseCommand):
    help = 'Load initial courses, achievements, and learning resources from fixtures'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reload data even if it already exists',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading',
        )

    def handle(self, *args, **options):
        # Check if data already exists
        courses_exist = Course.objects.exists()
        achievements_exist = Achievement.objects.exists()
        resources_exist = LearningResource.objects.exists()
        
        if courses_exist and achievements_exist and resources_exist and not options['force'] and not options['clear']:
            self.stdout.write(
                self.style.WARNING('Initial data already exists. Use --force to reload or --clear to clear first.')
            )
            return
        
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Course.objects.all().delete()
            Achievement.objects.all().delete()
            LearningResource.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))
        
        # Load the fixture
        self.stdout.write('Loading initial data from fixtures...')
        try:
            call_command('loaddata', 'initial_data', app_label='learning')
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded initial data!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading initial data: {str(e)}')
            ) 