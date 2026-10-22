from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase

from subjects.tests import vec
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
            embedding_vector=vec(1.0, 0.0), embedding_status='completed',
        )

        pipeline = RetrievalPipeline(PipelineConfig(name='t', similarity_threshold=0.0))
        results, _ = pipeline._search_chunks(vec(1.0, 0.0), subject.id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].material_name, material.file.name)


import json
import tempfile
from io import StringIO

from django.core.management import call_command

from retrieval.benchmark import first_relevant_rank
from retrieval.models import RetrievalExperiment
from retrieval.reranking import RankedChunk
from subjects.utils import load_embedding_model


class BenchmarkTest(TestCase):
    def test_rank_is_first_chunk_containing_an_expected_snippet(self):
        chunks = [RankedChunk(i, text, i, 1, 'a', 0.5) for i, text in enumerate(['intro', 'DDL is Data Definition Language'])]
        self.assertEqual(first_relevant_rank(chunks, 'data definition'), 2)
        self.assertEqual(first_relevant_rank(chunks, ['nope', 'INTRO']), 1)
        self.assertIsNone(first_relevant_rank(chunks, 'missing'))

    def test_command_scores_and_stores_a_run(self):
        user = get_user_model().objects.create_user('b', password='p')
        subject = Subject.objects.create(user=user, name='DB')
        material = SubjectMaterial.objects.create(subject=subject, file='a.pdf', file_type='PDF')
        model = load_embedding_model()
        for i, text in enumerate(['DDL stands for Data Definition Language.', 'Third normal form removes transitive dependencies.']):
            ContentChunk.objects.create(material=material, content=text, chunk_index=i,
                                        embedding_vector=model.encode(text).tolist(), embedding_status='completed')
        cases = [
            {'subject_id': subject.id, 'question': 'What does DDL stand for?', 'expected': 'Data Definition Language'},
            {'subject_id': subject.id, 'question': 'What is a B-tree index?', 'expected': 'B-tree'},
        ]
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump(cases, f)

        call_command('benchmark_retrieval', f.name, '--name', 'bench', stdout=StringIO())

        run = RetrievalExperiment.objects.get(name='bench')
        summary = json.loads(run.notes)
        self.assertEqual((summary['cases'], summary['hit_at_5'], summary['mrr']), (2, 0.5, 0.5))
        self.assertEqual(run.results.get(query='What does DDL stand for?').metrics['rank'], 1)
        self.assertFalse(run.results.get(query='What is a B-tree index?').metrics['hit'])


from retrieval.metrics import MetricsCollector


class MetricsScaleTest(TestCase):
    def test_similarity_metrics_ignore_reranker_logits(self):
        chunks = [RankedChunk(1, 'a', 0, 1, 'a.pdf', 0.6, reranked_score=7.3),
                  RankedChunk(2, 'b', 1, 1, 'a.pdf', 0.4, reranked_score=-4.0)]
        metric = MetricsCollector().record_retrieval('p', 'q', chunks, top_k=5, reranking_applied=True,
                                                    reranker_used='cross-encoder', total_latency_ms=12.0)
        self.assertAlmostEqual(metric.mean_similarity_score, 0.5)
        self.assertEqual(metric.top_score, 0.6)
        self.assertEqual((metric.total_latency_ms, metric.embedding_latency_ms), (12.0, 0.0))
