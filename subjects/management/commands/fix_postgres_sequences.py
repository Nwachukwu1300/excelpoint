from django.core.management.base import BaseCommand
from django.db import connection, models
from subjects.models import SubjectMaterial, ContentChunk, Flashcard, QuizQuestion


class Command(BaseCommand):
    help = 'Fix PostgreSQL sequences after migration from SQLite'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Fix sequences for all relevant tables
            tables_and_models = [
                ('subjects_subjectmaterial', SubjectMaterial),
                ('subjects_contentchunk', ContentChunk),
                ('subjects_flashcard', Flashcard),
                ('subjects_quizquestion', QuizQuestion),
            ]
            
            for table_name, model in tables_and_models:
                try:
                    # Get the current maximum ID
                    max_id = model.objects.aggregate(
                        max_id=models.Max('id')
                    )['max_id'] or 0
                    
                    # Reset the sequence to the max ID + 1
                    cursor.execute(
                        f"SELECT setval('{table_name}_id_seq', %s, true)",
                        [max_id + 1]
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Fixed sequence for {table_name}: set to {max_id + 1}'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error fixing sequence for {table_name}: {e}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS('PostgreSQL sequences have been fixed!')
        ) 