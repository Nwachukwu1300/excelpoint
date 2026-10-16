from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase

from subjects.models import ContentChunk, Subject, SubjectMaterial

from .pipeline import PipelineConfig, RetrievalPipeline


class SearchChunksTest(TestCase):
    def test_search_returns_material_file_name(self):
        user = get_user_model().objects.create_user(username='u', password='p')
        subject = Subject.objects.create(user=user, name='S')
        material = SubjectMaterial(subject=subject, file_type='PDF', status='COMPLETED')
        material.file.save('notes.pdf', ContentFile(b'x'), save=True)
        self.addCleanup(material.file.delete, save=False)
        ContentChunk.objects.create(
            material=material, content='hello', chunk_index=0,
            embedding_vector=[1.0, 0.0], embedding_status='completed',
        )

        pipeline = RetrievalPipeline(PipelineConfig(name='t', similarity_threshold=0.0))
        results, _ = pipeline._search_chunks([1.0, 0.0], subject.id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].material_name, material.file.name)
