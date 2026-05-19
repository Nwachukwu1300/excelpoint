"""
Experiment service for retrieval system A/B testing.

This module provides services for creating, running, and comparing
retrieval experiments. Experiments allow systematic testing of different
pipeline configurations to optimize retrieval quality.

Usage:
    from retrieval.experiments import RetrievalExperimentService

    service = RetrievalExperimentService()

    # Create an experiment
    experiment = service.create_experiment(
        name='test_reranking',
        description='Test cross-encoder reranking impact',
        pipeline_config={...}
    )

    # Run the experiment
    result = service.run_experiment('test_reranking', query='What is AI?', subject_id=1)

    # Compare experiments
    comparison = service.compare_experiments('baseline', 'test_reranking')
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from django.db.models import Avg, Count

from .models import (
    RetrievalExperiment,
    RetrievalExperimentResult,
    RetrievalPipelineConfig
)
from .pipeline import RetrievalPipeline, PipelineConfig
from .metrics import MetricsCollector

logger = logging.getLogger(__name__)


class ExperimentError(Exception):
    """Exception raised when experiment operations fail."""
    pass


class RetrievalExperimentService:
    """
    Service for managing retrieval experiments.

    Provides methods to create, run, and compare experiments for
    systematic A/B testing of retrieval configurations.

    Methods:
        create_experiment: Create a new experiment definition.
        run_experiment: Execute an experiment with a query.
        get_experiment: Get experiment details by name.
        get_experiment_results: Get all results for an experiment.
        compare_experiments: Compare metrics across experiments.
        delete_experiment: Delete an experiment and its results.
    """

    def create_experiment(
        self,
        name: str,
        description: str = '',
        pipeline_config: Optional[Dict[str, Any]] = None,
        notes: str = ''
    ) -> RetrievalExperiment:
        """
        Create a new experiment definition.

        Args:
            name: Unique name for the experiment.
            description: Human-readable description.
            pipeline_config: Pipeline configuration dictionary.
            notes: Additional notes.

        Returns:
            The created RetrievalExperiment instance.

        Raises:
            ExperimentError: If an experiment with this name already exists.
            ValueError: If the pipeline configuration is invalid.
        """
        if RetrievalExperiment.objects.filter(name=name).exists():
            raise ExperimentError(f"Experiment '{name}' already exists")

        # Validate pipeline config
        if pipeline_config:
            config = PipelineConfig.from_dict({
                'name': name,
                **pipeline_config
            })
            errors = config.validate()
            if errors:
                raise ValueError(f"Invalid pipeline configuration: {'; '.join(errors)}")
            pipeline_config = config.to_dict()
        else:
            # Use default configuration
            pipeline_config = PipelineConfig(name=name).to_dict()

        experiment = RetrievalExperiment.objects.create(
            name=name,
            description=description,
            pipeline_config=pipeline_config,
            notes=notes
        )

        logger.info(f"Created experiment: {name}")
        return experiment

    def get_experiment(self, name: str) -> RetrievalExperiment:
        """
        Get an experiment by name.

        Args:
            name: The experiment name.

        Returns:
            The RetrievalExperiment instance.

        Raises:
            ExperimentError: If the experiment is not found.
        """
        try:
            return RetrievalExperiment.objects.get(name=name)
        except RetrievalExperiment.DoesNotExist:
            raise ExperimentError(f"Experiment '{name}' not found")

    def list_experiments(self) -> List[Dict[str, Any]]:
        """
        List all experiments.

        Returns:
            A list of experiment summaries.
        """
        experiments = RetrievalExperiment.objects.all().order_by('-created_at')
        return [
            {
                'name': exp.name,
                'description': exp.description,
                'result_count': exp.get_result_count(),
                'created_at': exp.created_at.isoformat(),
                'pipeline_config': exp.pipeline_config
            }
            for exp in experiments
        ]

    def run_experiment(
        self,
        experiment_name: str,
        query: str,
        subject_id: int
    ) -> RetrievalExperimentResult:
        """
        Run an experiment with a query.

        Executes the experiment's pipeline configuration against the
        specified query and subject, recording the results.

        Args:
            experiment_name: The experiment name.
            query: The search query.
            subject_id: The subject to search within.

        Returns:
            The created RetrievalExperimentResult instance.

        Raises:
            ExperimentError: If the experiment is not found or execution fails.
        """
        experiment = self.get_experiment(experiment_name)

        # Create pipeline from experiment config
        config = PipelineConfig.from_dict(experiment.pipeline_config)
        pipeline = RetrievalPipeline(config)

        try:
            # Execute the pipeline
            result = pipeline.search(query=query, subject_id=subject_id)

            # Store results
            experiment_result = RetrievalExperimentResult.objects.create(
                experiment=experiment,
                query=query,
                subject_id=subject_id,
                results=[chunk.to_dict() for chunk in result.chunks],
                metrics=result.to_dict()
            )

            # Also record to metrics table for cross-analysis
            collector = MetricsCollector()
            collector.record_retrieval(
                pipeline_name=f"experiment:{experiment_name}",
                query=query,
                chunks=result.chunks,
                top_k=config.top_k,
                reranking_applied=result.reranking_applied,
                reranker_used=result.reranker_used,
                total_latency_ms=result.total_latency_ms,
                embedding_latency_ms=result.embedding_latency_ms,
                search_latency_ms=result.search_latency_ms,
                reranking_latency_ms=result.reranking_latency_ms
            )

            logger.info(
                f"Experiment '{experiment_name}' completed for query: {query[:50]}... "
                f"Retrieved {result.chunk_count} chunks in {result.total_latency_ms:.2f}ms"
            )

            return experiment_result

        except Exception as e:
            logger.error(f"Experiment '{experiment_name}' failed: {str(e)}")
            raise ExperimentError(f"Experiment execution failed: {str(e)}")

    def get_experiment_results(
        self,
        experiment_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get results for an experiment.

        Args:
            experiment_name: The experiment name.
            limit: Maximum number of results to return.

        Returns:
            A list of experiment result summaries.
        """
        experiment = self.get_experiment(experiment_name)

        results = experiment.results.all().order_by('-created_at')[:limit]
        return [
            {
                'id': r.id,
                'query': r.query,
                'subject_id': r.subject_id,
                'chunk_count': r.get_chunk_count(),
                'metrics_summary': r.get_metrics_summary(),
                'created_at': r.created_at.isoformat()
            }
            for r in results
        ]

    def get_experiment_stats(self, experiment_name: str) -> Dict[str, Any]:
        """
        Get aggregated statistics for an experiment.

        Args:
            experiment_name: The experiment name.

        Returns:
            A dictionary containing aggregated statistics.
        """
        experiment = self.get_experiment(experiment_name)
        results = experiment.results.all()

        if not results.exists():
            return {
                'experiment_name': experiment_name,
                'total_runs': 0,
                'message': 'No results found for this experiment'
            }

        # Aggregate metrics from stored JSON
        total_runs = results.count()
        latencies = []
        scores = []
        chunk_counts = []

        for r in results:
            metrics = r.metrics
            if 'total_latency_ms' in metrics:
                latencies.append(metrics['total_latency_ms'])
            if 'mean_score' in metrics:
                scores.append(metrics['mean_score'])
            if 'chunk_count' in metrics:
                chunk_counts.append(metrics['chunk_count'])

        return {
            'experiment_name': experiment_name,
            'description': experiment.description,
            'total_runs': total_runs,
            'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
            'avg_score': sum(scores) / len(scores) if scores else 0,
            'avg_chunk_count': sum(chunk_counts) / len(chunk_counts) if chunk_counts else 0,
            'pipeline_config': experiment.pipeline_config,
            'created_at': experiment.created_at.isoformat()
        }

    def compare_experiments(
        self,
        experiment_name_1: str,
        experiment_name_2: str
    ) -> Dict[str, Any]:
        """
        Compare two experiments side by side.

        Args:
            experiment_name_1: First experiment name.
            experiment_name_2: Second experiment name.

        Returns:
            A dictionary containing side-by-side comparison.
        """
        stats1 = self.get_experiment_stats(experiment_name_1)
        stats2 = self.get_experiment_stats(experiment_name_2)

        # Calculate differences
        comparison = {
            'experiment_1': stats1,
            'experiment_2': stats2,
            'comparison': {}
        }

        # Compare key metrics
        if stats1['total_runs'] > 0 and stats2['total_runs'] > 0:
            comparison['comparison'] = {
                'latency_diff_ms': stats2['avg_latency_ms'] - stats1['avg_latency_ms'],
                'latency_diff_percent': (
                    (stats2['avg_latency_ms'] - stats1['avg_latency_ms']) /
                    stats1['avg_latency_ms'] * 100
                    if stats1['avg_latency_ms'] > 0 else 0
                ),
                'score_diff': stats2['avg_score'] - stats1['avg_score'],
                'score_diff_percent': (
                    (stats2['avg_score'] - stats1['avg_score']) /
                    stats1['avg_score'] * 100
                    if stats1['avg_score'] > 0 else 0
                ),
                'chunk_count_diff': stats2['avg_chunk_count'] - stats1['avg_chunk_count'],
            }

            # Determine winner for each metric
            comparison['comparison']['latency_winner'] = (
                experiment_name_1 if stats1['avg_latency_ms'] < stats2['avg_latency_ms']
                else experiment_name_2
            )
            comparison['comparison']['score_winner'] = (
                experiment_name_1 if stats1['avg_score'] > stats2['avg_score']
                else experiment_name_2
            )

        return comparison

    def delete_experiment(self, name: str) -> bool:
        """
        Delete an experiment and all its results.

        Args:
            name: The experiment name.

        Returns:
            True if deleted, False if not found.
        """
        try:
            experiment = RetrievalExperiment.objects.get(name=name)
            result_count = experiment.results.count()
            experiment.delete()
            logger.info(f"Deleted experiment '{name}' with {result_count} results")
            return True
        except RetrievalExperiment.DoesNotExist:
            return False

    def clone_experiment(
        self,
        source_name: str,
        new_name: str,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> RetrievalExperiment:
        """
        Clone an existing experiment with optional configuration changes.

        Args:
            source_name: The source experiment name.
            new_name: The new experiment name.
            config_overrides: Optional configuration values to override.

        Returns:
            The created RetrievalExperiment instance.

        Raises:
            ExperimentError: If source not found or new name already exists.
        """
        source = self.get_experiment(source_name)

        if RetrievalExperiment.objects.filter(name=new_name).exists():
            raise ExperimentError(f"Experiment '{new_name}' already exists")

        # Copy and override config
        new_config = source.pipeline_config.copy()
        new_config['name'] = new_name
        if config_overrides:
            new_config.update(config_overrides)

        return self.create_experiment(
            name=new_name,
            description=f"Cloned from '{source_name}'. {source.description}",
            pipeline_config=new_config,
            notes=source.notes
        )

    def run_experiment_batch(
        self,
        experiment_name: str,
        queries: List[str],
        subject_id: int
    ) -> List[RetrievalExperimentResult]:
        """
        Run an experiment with multiple queries.

        Args:
            experiment_name: The experiment name.
            queries: List of search queries.
            subject_id: The subject to search within.

        Returns:
            A list of experiment results.
        """
        results = []
        for query in queries:
            try:
                result = self.run_experiment(experiment_name, query, subject_id)
                results.append(result)
            except ExperimentError as e:
                logger.warning(f"Query failed in batch: {query[:50]}... Error: {str(e)}")

        logger.info(
            f"Batch experiment '{experiment_name}' completed: "
            f"{len(results)}/{len(queries)} queries successful"
        )
        return results
