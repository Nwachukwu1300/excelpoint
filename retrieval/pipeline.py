"""
Configurable retrieval pipeline module.

This module provides a flexible retrieval pipeline that can be configured
at runtime with different chunking strategies, embedding models, rerankers,
and other parameters.

The pipeline executes the following flow:
1. Receive query
2. Embed query using configured embedding model
3. Search vector store for similar chunks
4. Optionally rerank results
5. Return ranked chunks with scores and timing metrics

Usage:
    from retrieval.pipeline import RetrievalPipeline, PipelineConfig

    config = PipelineConfig(
        name='my_pipeline',
        embedding_model='sentence-transformers/all-MiniLM-L6-v2',
        top_k=10,
        reranking_enabled=True,
        reranker_name='cross_encoder'
    )
    pipeline = RetrievalPipeline(config)
    results = pipeline.search(query="What is machine learning?", subject_id=1)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import time
import logging
import numpy as np

from .embeddings import EmbeddingFactory, BaseEmbedding, EmbeddingError
from .reranking import RerankerFactory, BaseReranker, RankedChunk

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """
    Configuration for a retrieval pipeline.

    This configuration defines all parameters needed to run a retrieval
    pipeline, including embedding model, search parameters, and reranking.

    Attributes:
        name: Unique identifier for this pipeline configuration.
        description: Human-readable description of the pipeline.
        chunking_strategy: The chunking strategy to use (for new content).
        chunking_params: Parameters for the chunking strategy.
        embedding_model: The embedding model to use for query encoding.
        top_k: Number of results to retrieve from vector search.
        similarity_threshold: Minimum similarity score for results.
        reranking_enabled: Whether to apply reranking.
        reranker_name: The reranker to use if reranking is enabled.
        reranker_params: Parameters for the reranker.
    """
    name: str
    description: str = ""
    chunking_strategy: str = "overlap"
    chunking_params: Dict[str, Any] = field(default_factory=lambda: {
        'chunk_size': 1000,
        'overlap_size': 200
    })
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    top_k: int = 10
    similarity_threshold: float = 0.15
    reranking_enabled: bool = False
    reranker_name: str = "cross_encoder"
    reranker_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineConfig':
        """
        Create a PipelineConfig from a dictionary.

        Args:
            data: Dictionary containing configuration values.

        Returns:
            A PipelineConfig instance.
        """
        return cls(
            name=data.get('name', 'default'),
            description=data.get('description', ''),
            chunking_strategy=data.get('chunking_strategy', 'overlap'),
            chunking_params=data.get('chunking_params', {
                'chunk_size': 1000,
                'overlap_size': 200
            }),
            embedding_model=data.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2'),
            top_k=data.get('top_k', 10),
            similarity_threshold=data.get('similarity_threshold', 0.15),
            reranking_enabled=data.get('reranking_enabled', False),
            reranker_name=data.get('reranker_name', 'cross_encoder'),
            reranker_params=data.get('reranker_params', {})
        )

    def validate(self) -> List[str]:
        """
        Validate the configuration.

        Returns:
            A list of validation error messages. Empty if valid.
        """
        errors = []

        if not self.name:
            errors.append("Pipeline name is required")

        if self.top_k < 1:
            errors.append("top_k must be at least 1")

        if not 0 <= self.similarity_threshold <= 1:
            errors.append("similarity_threshold must be between 0 and 1")

        return errors


@dataclass
class RetrievalResult:
    """
    Result of a retrieval pipeline execution.

    Attributes:
        query: The original query.
        chunks: List of retrieved and ranked chunks.
        pipeline_name: The name of the pipeline used.
        total_latency_ms: Total execution time in milliseconds.
        embedding_latency_ms: Time spent on query embedding.
        search_latency_ms: Time spent on vector search.
        reranking_latency_ms: Time spent on reranking (if applied).
        reranking_applied: Whether reranking was applied.
        embedding_model: The embedding model used.
        reranker_used: The reranker used (if reranking was applied).
    """
    query: str
    chunks: List[RankedChunk]
    pipeline_name: str
    total_latency_ms: float
    embedding_latency_ms: float
    search_latency_ms: float
    reranking_latency_ms: Optional[float]
    reranking_applied: bool
    embedding_model: str
    reranker_used: Optional[str]

    @property
    def chunk_count(self) -> int:
        """Return the number of retrieved chunks."""
        return len(self.chunks)

    @property
    def mean_score(self) -> float:
        """Return the mean similarity/reranked score."""
        if not self.chunks:
            return 0.0
        scores = [
            c.reranked_score if c.reranked_score is not None else c.initial_score
            for c in self.chunks
        ]
        return sum(scores) / len(scores)

    @property
    def top_score(self) -> float:
        """Return the highest similarity/reranked score."""
        if not self.chunks:
            return 0.0
        scores = [
            c.reranked_score if c.reranked_score is not None else c.initial_score
            for c in self.chunks
        ]
        return max(scores)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            'query': self.query,
            'chunks': [c.to_dict() for c in self.chunks],
            'pipeline_name': self.pipeline_name,
            'total_latency_ms': self.total_latency_ms,
            'embedding_latency_ms': self.embedding_latency_ms,
            'search_latency_ms': self.search_latency_ms,
            'reranking_latency_ms': self.reranking_latency_ms,
            'reranking_applied': self.reranking_applied,
            'embedding_model': self.embedding_model,
            'reranker_used': self.reranker_used,
            'chunk_count': self.chunk_count,
            'mean_score': self.mean_score,
            'top_score': self.top_score,
        }


class RetrievalPipeline:
    """
    Configurable retrieval pipeline.

    Executes a full retrieval flow: embed query → search → rerank → return.
    The pipeline is configured via a PipelineConfig object that specifies
    all parameters.

    The pipeline integrates with the existing ContentChunk model from the
    subjects app for vector search.

    Attributes:
        config: The pipeline configuration.
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize the retrieval pipeline.

        Args:
            config: The pipeline configuration.

        Raises:
            ValueError: If the configuration is invalid.
        """
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid pipeline configuration: {'; '.join(errors)}")

        self._config = config
        self._embedding_model: Optional[BaseEmbedding] = None
        self._reranker: Optional[BaseReranker] = None

    @property
    def config(self) -> PipelineConfig:
        """Return the pipeline configuration."""
        return self._config

    def _get_embedding_model(self) -> BaseEmbedding:
        """
        Get or create the embedding model.

        Returns:
            The embedding model instance.
        """
        if self._embedding_model is None:
            self._embedding_model = EmbeddingFactory.get_embedding_model(
                self._config.embedding_model
            )
        return self._embedding_model

    def _get_reranker(self) -> BaseReranker:
        """
        Get or create the reranker.

        Returns:
            The reranker instance.
        """
        if self._reranker is None:
            self._reranker = RerankerFactory.get_reranker(
                self._config.reranker_name,
                **self._config.reranker_params
            )
        return self._reranker

    def _embed_query(self, query: str) -> tuple[List[float], float]:
        """
        Embed the query and return timing.

        Args:
            query: The query string.

        Returns:
            A tuple of (embedding vector, latency in ms).
        """
        start_time = time.perf_counter()
        model = self._get_embedding_model()
        embedding = model.embed_single(query)
        latency_ms = (time.perf_counter() - start_time) * 1000
        return embedding, latency_ms

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity score between -1 and 1.
        """
        a = np.array(vec1)
        b = np.array(vec2)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def _search_chunks(
        self,
        query_embedding: List[float],
        subject_id: int
    ) -> tuple[List[RankedChunk], float]:
        """
        Search for similar chunks in the vector store.

        Args:
            query_embedding: The embedded query vector.
            subject_id: The subject to search within.

        Returns:
            A tuple of (list of RankedChunk, latency in ms).
        """
        start_time = time.perf_counter()

        # Import here to avoid circular imports
        from subjects.models import ContentChunk

        # Get all chunks with embeddings for this subject
        chunks = ContentChunk.objects.filter(
            material__subject_id=subject_id,
            embedding_status='completed',
            embedding_vector__isnull=False
        ).select_related('material').order_by('material_id', 'chunk_index')

        results = []
        for chunk in chunks:
            if not chunk.embedding_vector:
                continue

            # Calculate similarity
            similarity = self._cosine_similarity(query_embedding, chunk.embedding_vector)

            # Apply threshold
            if similarity >= self._config.similarity_threshold:
                results.append(RankedChunk(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    material_id=chunk.material_id,
                    material_name=chunk.material.name if chunk.material else '',
                    initial_score=similarity,
                    reranked_score=None,
                    metadata={
                        'material_type': chunk.material.file_type if chunk.material else '',
                        'created_at': chunk.created_at.isoformat() if chunk.created_at else '',
                    }
                ))

        # Sort by similarity and take top_k
        results.sort(key=lambda x: x.initial_score, reverse=True)
        results = results[:self._config.top_k]

        latency_ms = (time.perf_counter() - start_time) * 1000
        return results, latency_ms

    def _rerank_chunks(
        self,
        query: str,
        chunks: List[RankedChunk]
    ) -> tuple[List[RankedChunk], float]:
        """
        Rerank chunks if reranking is enabled.

        Args:
            query: The original query.
            chunks: List of chunks to rerank.

        Returns:
            A tuple of (reranked chunks, latency in ms).
        """
        start_time = time.perf_counter()
        reranker = self._get_reranker()
        reranked = reranker.rerank(query, chunks)
        latency_ms = (time.perf_counter() - start_time) * 1000
        return reranked, latency_ms

    def search(self, query: str, subject_id: int) -> RetrievalResult:
        """
        Execute the retrieval pipeline.

        Args:
            query: The search query.
            subject_id: The subject to search within.

        Returns:
            A RetrievalResult containing chunks and metrics.

        Raises:
            EmbeddingError: If query embedding fails.
            ValueError: If subject_id is invalid.
        """
        total_start = time.perf_counter()

        if not query.strip():
            raise ValueError("Query cannot be empty")

        if subject_id < 1:
            raise ValueError("Invalid subject_id")

        logger.info(
            f"Executing pipeline '{self._config.name}' for query: {query[:50]}..."
        )

        # Step 1: Embed query
        try:
            query_embedding, embedding_latency = self._embed_query(query)
        except EmbeddingError as e:
            logger.error(f"Query embedding failed: {str(e)}")
            raise

        # Step 2: Search vector store
        chunks, search_latency = self._search_chunks(query_embedding, subject_id)
        logger.debug(f"Found {len(chunks)} chunks matching query")

        # Step 3: Rerank if enabled
        reranking_latency = None
        reranker_used = None
        if self._config.reranking_enabled and chunks:
            chunks, reranking_latency = self._rerank_chunks(query, chunks)
            reranker_used = self._config.reranker_name
            logger.debug(f"Reranked {len(chunks)} chunks using {reranker_used}")

        total_latency = (time.perf_counter() - total_start) * 1000

        result = RetrievalResult(
            query=query,
            chunks=chunks,
            pipeline_name=self._config.name,
            total_latency_ms=total_latency,
            embedding_latency_ms=embedding_latency,
            search_latency_ms=search_latency,
            reranking_latency_ms=reranking_latency,
            reranking_applied=self._config.reranking_enabled and reranker_used is not None,
            embedding_model=self._config.embedding_model,
            reranker_used=reranker_used
        )

        logger.info(
            f"Pipeline '{self._config.name}' completed in {total_latency:.2f}ms. "
            f"Retrieved {result.chunk_count} chunks, top score: {result.top_score:.4f}"
        )

        return result


class PipelineManager:
    """
    Manager for retrieval pipeline configurations.

    Provides methods to create, store, and retrieve pipeline configurations
    from the database.
    """

    @staticmethod
    def create_pipeline(config: PipelineConfig) -> 'RetrievalPipelineConfig':
        """
        Create and save a pipeline configuration.

        Args:
            config: The pipeline configuration.

        Returns:
            The saved RetrievalPipelineConfig model instance.
        """
        from .models import RetrievalPipelineConfig as PipelineConfigModel

        pipeline_config = PipelineConfigModel(
            name=config.name,
            description=config.description,
            config=config.to_dict()
        )
        pipeline_config.save()

        logger.info(f"Created pipeline configuration: {config.name}")
        return pipeline_config

    @staticmethod
    def get_pipeline(name: str) -> RetrievalPipeline:
        """
        Get a retrieval pipeline by name.

        Args:
            name: The pipeline configuration name.

        Returns:
            A RetrievalPipeline instance.

        Raises:
            ValueError: If the pipeline is not found.
        """
        from .models import RetrievalPipelineConfig as PipelineConfigModel

        try:
            pipeline_config = PipelineConfigModel.objects.get(name=name)
        except PipelineConfigModel.DoesNotExist:
            raise ValueError(f"Pipeline configuration not found: {name}")

        config = PipelineConfig.from_dict(pipeline_config.config)
        return RetrievalPipeline(config)

    @staticmethod
    def list_pipelines() -> List[Dict[str, Any]]:
        """
        List all saved pipeline configurations.

        Returns:
            A list of pipeline configuration summaries.
        """
        from .models import RetrievalPipelineConfig as PipelineConfigModel

        pipelines = PipelineConfigModel.objects.all().order_by('-created_at')
        return [
            {
                'name': p.name,
                'description': p.description,
                'created_at': p.created_at.isoformat(),
                'updated_at': p.updated_at.isoformat(),
                'config': p.config
            }
            for p in pipelines
        ]

    @staticmethod
    def delete_pipeline(name: str) -> bool:
        """
        Delete a pipeline configuration by name.

        Args:
            name: The pipeline configuration name.

        Returns:
            True if deleted, False if not found.
        """
        from .models import RetrievalPipelineConfig as PipelineConfigModel

        try:
            pipeline_config = PipelineConfigModel.objects.get(name=name)
            pipeline_config.delete()
            logger.info(f"Deleted pipeline configuration: {name}")
            return True
        except PipelineConfigModel.DoesNotExist:
            return False
