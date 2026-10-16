import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from subjects.tests import vec
from subjects.models import ContentChunk, Subject, SubjectMaterial
from subjects.tasks import process_material

MEDIA = tempfile.mkdtemp()
CHUNKS = [
    {'content': 'one', 'chunk_index': 0, 'embedding_vector': vec(0.1)},
    {'content': 'two', 'chunk_index': 1, 'embedding_vector': vec(0.2)},
]


@override_settings(MEDIA_ROOT=MEDIA)
@patch('subjects.tasks.generate_flashcards.apply_async')
@patch('subjects.tasks.generate_quiz_from_material.apply_async')
@patch('subjects.utils.ContentProcessor.process_file', return_value=CHUNKS)
class ProcessMaterialTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_reprocessing_replaces_chunks(self, *_):
        user = get_user_model().objects.create_user('u', password='p')
        material = SubjectMaterial(subject=Subject.objects.create(user=user, name='S'), file_type='PDF')
        material.file.save('a.pdf', ContentFile(b'x'))

        process_material(material.id)
        process_material(material.id)

        material.refresh_from_db()
        self.assertEqual(material.status, 'COMPLETED')
        self.assertEqual(list(ContentChunk.objects.filter(material=material).values_list('content', flat=True).order_by('chunk_index')), ['one', 'two'])
