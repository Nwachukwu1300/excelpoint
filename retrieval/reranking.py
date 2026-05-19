"""
Reranking module for improving retrieval quality.

This module provides reranking strategies to reorder retrieved chunks
by relevance before they are returned. Reranking can significantly
improve retrieval quality by using more sophisticated scoring methods
than the initial similarity search.

Supported rerankers:
- CrossEncoderReranker: Uses a cross-encoder model for accurate relevance scoring
- KeywordOverlapReranker: Simple keyword-based scoring for fast reranking

Usage:
    from retrieval.reranking import RerankerFactory

    reranker = RerankerFactory.get_reranker('cross_encoder')
    reranked_chunks = reranker.rerank(query, chunks_with_scores)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Set
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class RankedChunk:
    """
    Represents a chunk with ranking scores.

    Attributes:
        chunk_id: The unique identifier of the chunk.
        content: The text content of the chunk.
        chunk_index: The position of this chunk in the original document.
        material_id: The ID of the source material.
        material_name: The name of the source material.
        initial_score: The similarity score from initial retrieval.
        reranked_score: The score after reranking (if reranking was applied).
        metadata: Additional metadata about the chunk.
    """
    chunk_id: int
    content: str
    chunk_index: int
    material_id: int
    material_name: str
    initial_score: float
    reranked_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the ranked chunk to a dictionary representation."""
        return asdict(self)

    @classmethod
    def from_search_result(cls, result: Dict[str, Any]) -> 'RankedChunk':
        """
        Create a RankedChunk from a vector search result.

        Args:
            result: A dictionary from VectorSearchService.search_by_query()

        Returns:
            A RankedChunk instance.
        """
        return cls(
            chunk_id=result.get('chunk_id', 0),
            content=result.get('content', ''),
            chunk_index=result.get('chunk_index', 0),
            material_id=result.get('material_id', 0),
            material_name=result.get('material_name', ''),
            initial_score=result.get('similarity_score', 0.0),
            reranked_score=None,
            metadata=result.get('metadata', {})
        )


class BaseReranker(ABC):
    """
    Abstract base class for all reranking strategies.

    All rerankers must implement the rerank() method which takes a query
    and a list of chunks with initial scores, and returns the same list
    reordered with updated scores.
    """

    @property
    @abstractmethod
    def reranker_name(self) -> str:
        """Return the name of this reranking strategy."""
        pass

    @abstractmethod
    def rerank(
        self,
        query: str,
        chunks: List[RankedChunk]
    ) -> List[RankedChunk]:
        """
        Rerank a list of chunks based on their relevance to the query.

        Args:
            query: The search query.
            chunks: A list of RankedChunk objects with initial scores.

        Returns:
            The same list of chunks, reordered by reranked_score in descending order.
        """
        pass

    def get_reranker_info(self) -> Dict[str, Any]:
        """
        Get information about this reranker.

        Returns:
            A dictionary containing reranker metadata.
        """
        return {
            'reranker_name': self.reranker_name,
            'type': self.__class__.__name__
        }


class CrossEncoderReranker(BaseReranker):
    """
    Cross-encoder based reranking.

    Uses a cross-encoder model to score each query-chunk pair directly.
    This is more accurate than bi-encoder similarity but slower since
    it cannot pre-compute embeddings.

    The default model is 'cross-encoder/ms-marco-MiniLM-L6-v2' which is
    optimized for passage reranking.

    Attributes:
        model_name: The cross-encoder model to use.
    """

    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L6-v2'):
        """
        Initialize the cross-encoder reranker.

        Args:
            model_name: The cross-encoder model to use.
        """
        self._model_name = model_name
        self._model = None

    def _load_model(self):
        """
        Lazy-load the cross-encoder model.

        Returns:
            The loaded CrossEncoder model.

        Raises:
            RuntimeError: If the model cannot be loaded.
        """
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading CrossEncoder model: {self._model_name}")
                self._model = CrossEncoder(self._model_name)
                logger.info(f"Loaded CrossEncoder model: {self._model_name}")
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers package not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load CrossEncoder model '{self._model_name}': {str(e)}"
                )

        return self._model

    @property
    def reranker_name(self) -> str:
        """Return the reranker name."""
        return f"cross_encoder/{self._model_name}"

    def rerank(
        self,
        query: str,
        chunks: List[RankedChunk]
    ) -> List[RankedChunk]:
        """
        Rerank chunks using cross-encoder scoring.

        Args:
            query: The search query.
            chunks: A list of RankedChunk objects.

        Returns:
            Chunks reordered by cross-encoder relevance score.
        """
        if not chunks:
            return []

        if not query.strip():
            logger.warning("Empty query provided to CrossEncoderReranker")
            return chunks

        try:
            model = self._load_model()

            # Create query-chunk pairs
            pairs = [[query, chunk.content] for chunk in chunks]

            # Get cross-encoder scores
            scores = model.predict(pairs)

            # Update chunks with reranked scores
            for i, chunk in enumerate(chunks):
                chunk.reranked_score = float(scores[i])

            # Sort by reranked score (descending)
            reranked = sorted(chunks, key=lambda x: x.reranked_score or 0, reverse=True)

            logger.debug(
                f"CrossEncoder reranked {len(chunks)} chunks. "
                f"Top score: {reranked[0].reranked_score:.4f} "
                f"(was {reranked[0].initial_score:.4f})"
            )

            return reranked

        except Exception as e:
            logger.error(f"CrossEncoder reranking failed: {str(e)}")
            # Return original order if reranking fails
            for chunk in chunks:
                chunk.reranked_score = chunk.initial_score
            return chunks


class KeywordOverlapReranker(BaseReranker):
    """
    Keyword-based reranking using term overlap.

    Scores chunks by counting the overlap of significant keywords
    between the query and chunk content. This is a fast, simple
    reranking method that doesn't require ML models.

    The scoring considers:
    - Exact keyword matches (case-insensitive)
    - Normalized by total unique keywords
    - Combines with initial score using configurable weight

    Attributes:
        initial_score_weight: Weight for the initial similarity score (0-1).
        min_keyword_length: Minimum length for a word to be considered a keyword.
    """

    # Common stop words to exclude from keyword matching
    STOP_WORDS: Set[str] = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
        'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'not', 'only', 'same', 'so', 'than', 'too', 'very',
        'just', 'also', 'now', 'here', 'there', 'then', 'once', 'if', 'about',
    }

    def __init__(
        self,
        initial_score_weight: float = 0.3,
        min_keyword_length: int = 3
    ):
        """
        Initialize the keyword overlap reranker.

        Args:
            initial_score_weight: Weight for combining initial score (0-1).
                Final score = (1-weight) * keyword_score + weight * initial_score
            min_keyword_length: Minimum length for keywords. Defaults to 3.

        Raises:
            ValueError: If initial_score_weight is not in [0, 1].
        """
        if not 0 <= initial_score_weight <= 1:
            raise ValueError("initial_score_weight must be between 0 and 1")
        if min_keyword_length < 1:
            raise ValueError("min_keyword_length must be at least 1")

        self._initial_score_weight = initial_score_weight
        self._min_keyword_length = min_keyword_length

    @property
    def reranker_name(self) -> str:
        """Return the reranker name."""
        return "keyword_overlap"

    def _extract_keywords(self, text: str) -> Set[str]:
        """
        Extract keywords from text.

        Args:
            text: The input text.

        Returns:
            A set of lowercase keywords.
        """
        # Convert to lowercase and split into words
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter: remove stop words and short words
        keywords = {
            word for word in words
            if (
                word not in self.STOP_WORDS and
                len(word) >= self._min_keyword_length and
                not word.isdigit()
            )
        }

        return keywords

    def _calculate_overlap_score(
        self,
        query_keywords: Set[str],
        chunk_keywords: Set[str]
    ) -> float:
        """
        Calculate normalized keyword overlap score.

        Args:
            query_keywords: Keywords from the query.
            chunk_keywords: Keywords from the chunk.

        Returns:
            Overlap score between 0 and 1.
        """
        if not query_keywords:
            return 0.0

        # Count matching keywords
        matches = query_keywords.intersection(chunk_keywords)

        # Normalize by query keywords (recall-oriented)
        score = len(matches) / len(query_keywords)

        return score

    def rerank(
        self,
        query: str,
        chunks: List[RankedChunk]
    ) -> List[RankedChunk]:
        """
        Rerank chunks using keyword overlap scoring.

        Args:
            query: The search query.
            chunks: A list of RankedChunk objects.

        Returns:
            Chunks reordered by combined keyword overlap and initial scores.
        """
        if not chunks:
            return []

        if not query.strip():
            logger.warning("Empty query provided to KeywordOverlapReranker")
            for chunk in chunks:
                chunk.reranked_score = chunk.initial_score
            return chunks

        # Extract query keywords once
        query_keywords = self._extract_keywords(query)

        if not query_keywords:
            logger.debug("No significant keywords found in query")
            for chunk in chunks:
                chunk.reranked_score = chunk.initial_score
            return sorted(chunks, key=lambda x: x.initial_score, reverse=True)

        # Score each chunk
        for chunk in chunks:
            chunk_keywords = self._extract_keywords(chunk.content)
            overlap_score = self._calculate_overlap_score(query_keywords, chunk_keywords)

            # Combine scores
            chunk.reranked_score = (
                (1 - self._initial_score_weight) * overlap_score +
                self._initial_score_weight * chunk.initial_score
            )

        # Sort by reranked score (descending)
        reranked = sorted(chunks, key=lambda x: x.reranked_score or 0, reverse=True)

        logger.debug(
            f"KeywordOverlap reranked {len(chunks)} chunks. "
            f"Query keywords: {len(query_keywords)}. "
            f"Top score: {reranked[0].reranked_score:.4f}"
        )

        return reranked


class RerankerFactory:
    """
    Factory class for creating reranker instances.

    Provides a centralized way to instantiate rerankers by name,
    supporting runtime selection of reranking strategies.

    Supported rerankers:
        - 'cross_encoder': CrossEncoderReranker
        - 'keyword_overlap': KeywordOverlapReranker

    Usage:
        reranker = RerankerFactory.get_reranker('cross_encoder')
        reranked = reranker.rerank(query, chunks)
    """

    RERANKERS = {
        'cross_encoder': CrossEncoderReranker,
        'keyword_overlap': KeywordOverlapReranker,
    }

    # Aliases for convenience
    ALIASES = {
        'ce': 'cross_encoder',
        'crossencoder': 'cross_encoder',
        'cross-encoder': 'cross_encoder',
        'keyword': 'keyword_overlap',
        'keywords': 'keyword_overlap',
        'overlap': 'keyword_overlap',
    }

    @classmethod
    def get_reranker(cls, name: str, **kwargs) -> BaseReranker:
        """
        Get a reranker instance by name.

        Args:
            name: The name of the reranker.
            **kwargs: Reranker-specific parameters.
                - cross_encoder: model_name (str)
                - keyword_overlap: initial_score_weight (float), min_keyword_length (int)

        Returns:
            A BaseReranker instance.

        Raises:
            ValueError: If the reranker name is not recognized.
        """
        name = name.lower().strip()

        # Check aliases
        if name in cls.ALIASES:
            name = cls.ALIASES[name]

        if name not in cls.RERANKERS:
            available = ', '.join(cls.RERANKERS.keys())
            raise ValueError(
                f"Unknown reranker: '{name}'. "
                f"Available rerankers: {available}"
            )

        reranker_class = cls.RERANKERS[name]
        logger.debug(f"Creating {name} reranker with params: {kwargs}")

        try:
            return reranker_class(**kwargs)
        except TypeError as e:
            raise ValueError(f"Invalid parameters for {name} reranker: {e}")

    @classmethod
    def list_rerankers(cls) -> List[str]:
        """
        List all available rerankers.

        Returns:
            A list of reranker names.
        """
        return list(cls.RERANKERS.keys())

    @classmethod
    def get_reranker_info(cls, name: str) -> Dict[str, Any]:
        """
        Get information about a specific reranker.

        Args:
            name: The name of the reranker.

        Returns:
            A dictionary containing reranker information.
        """
        name = name.lower().strip()
        if name in cls.ALIASES:
            name = cls.ALIASES[name]

        if name not in cls.RERANKERS:
            available = ', '.join(cls.RERANKERS.keys())
            raise ValueError(
                f"Unknown reranker: '{name}'. "
                f"Available rerankers: {available}"
            )

        reranker_class = cls.RERANKERS[name]

        # Extract parameter info
        import inspect
        sig = inspect.signature(reranker_class.__init__)
        params = {
            param_name: {
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'required': param.default == inspect.Parameter.empty
            }
            for param_name, param in sig.parameters.items()
            if param_name != 'self'
        }

        return {
            'name': name,
            'description': reranker_class.__doc__,
            'parameters': params
        }
