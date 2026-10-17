import json
from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from retrieval.benchmark import run_benchmark
from retrieval.models import RetrievalExperiment, RetrievalExperimentResult
from retrieval.pipeline import PipelineConfig, RetrievalPipeline


class Command(BaseCommand):
    help = "Score retrieval (hit@k, MRR) on a labelled question set and store the run as an experiment"

    def add_arguments(self, parser):
        parser.add_argument('dataset', help='JSON list of {subject_id, question, expected}')
        parser.add_argument('--top-k', type=int, default=5)
        parser.add_argument('--threshold', type=float, default=0.3)
        parser.add_argument('--rerank', action='store_true', help='Apply the cross-encoder reranker')
        parser.add_argument('--name', help='Experiment name (default: timestamped)')

    def handle(self, *args, dataset, top_k, threshold, rerank, name, **options):
        try:
            with open(dataset) as f:
                cases = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f"Could not read dataset: {e}")
        missing = [i for i, c in enumerate(cases) if not {'subject_id', 'question', 'expected'} <= c.keys()]
        if missing:
            raise CommandError(f"Cases {missing} need subject_id, question and expected")

        name = name or f"benchmark-{timezone.now():%Y%m%d-%H%M%S}"
        config = PipelineConfig(name=name, top_k=top_k, similarity_threshold=threshold, reranking_enabled=rerank)
        rows, summary = run_benchmark(cases, RetrievalPipeline(config))

        experiment = RetrievalExperiment.objects.create(
            name=name, description=f"Benchmark on {dataset}",
            pipeline_config=asdict(config), notes=json.dumps(summary),
        )
        RetrievalExperimentResult.objects.bulk_create([
            RetrievalExperimentResult(
                experiment=experiment, query=r['question'], subject_id=r['subject_id'],
                results=r['retrieved'], metrics={k: r[k] for k in ('rank', 'hit', 'top_score', 'latency_ms')},
            )
            for r in rows
        ])

        for r in rows:
            mark = f"rank {r['rank']}" if r['hit'] else 'MISS'
            self.stdout.write(f"  [{mark:>7}] {r['question']}")
        self.stdout.write(self.style.SUCCESS(f"{name}: {json.dumps(summary)}"))
