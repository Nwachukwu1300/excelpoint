"""
Embedding model support for multiple providers.

This module provides a unified interface for generating text embeddings
using different embedding models. Supports both cloud-based (OpenAI) and
local (SentenceTransformers) models.

Supported models:
- OpenAI: text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large
- SentenceTransformers: all-MiniLM-L6-v2, all-mpnet-base-v2, and custom models

Usage:
    from retrieval.embeddings import EmbeddingFactory

    model = EmbeddingFactory.get_embedding_model('sentence-transformers/all-MiniLM-L6-v2')
    embeddings = model.embed(["Hello world", "Another text"])
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Exception raised when embedding generation fails."""
    pass


class BaseEmbedding(ABC):
    """
    Abstract base class for all embedding models.

    All embedding models must implement the embed() method which takes
    a list of strings and returns a list of embedding vectors.

    Properties:
        model_name: The identifier of the embedding model.
        dimensions: The dimensionality of the output embeddings.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name/identifier of this embedding model."""
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the dimensionality of embeddings produced by this model."""
        pass

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: A list of strings to embed.

        Returns:
            A list of embedding vectors, where each vector is a list of floats.
            The length of the returned list matches the length of the input texts.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        pass

    def embed_single(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.

        Args:
            text: The text to embed.

        Returns:
            A single embedding vector as a list of floats.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        result = self.embed([text])
        return result[0]

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about this embedding model.

        Returns:
            A dictionary containing model metadata.
        """
        return {
            'model_name': self.model_name,
            'dimensions': self.dimensions,
            'provider': self.__class__.__name__
        }


class OpenAIEmbedding(BaseEmbedding):
    """
    OpenAI embedding model implementation.

    Uses OpenAI's embedding API to generate text embeddings.
    Supports text-embedding-ada-002, text-embedding-3-small, and text-embedding-3-large.

    Attributes:
        model: The OpenAI model identifier.

    Note:
        Requires OPENAI_API_KEY to be set in environment or Django settings.
    """

    # Model configurations: model_name -> dimensions
    MODEL_CONFIGS = {
        'text-embedding-ada-002': 1536,
        'text-embedding-3-small': 1536,
        'text-embedding-3-large': 3072,
    }

    def __init__(self, model: str = 'text-embedding-3-small'):
        """
        Initialize the OpenAI embedding model.

        Args:
            model: The OpenAI model to use. Defaults to 'text-embedding-3-small'.

        Raises:
            ValueError: If the model is not supported.
            EmbeddingError: If the OpenAI API key is not configured.
        """
        if model not in self.MODEL_CONFIGS:
            available = ', '.join(self.MODEL_CONFIGS.keys())
            raise ValueError(
                f"Unsupported OpenAI model: '{model}'. "
                f"Available models: {available}"
            )

        self._model = model
        self._dimensions = self.MODEL_CONFIGS[model]
        self._client = None

    def _get_client(self):
        """
        Get or create the OpenAI client.

        Returns:
            The OpenAI client instance.

        Raises:
            EmbeddingError: If the API key is not configured.
        """
        if self._client is None:
            api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')

            if not api_key:
                raise EmbeddingError(
                    "OpenAI API key not configured. Set OPENAI_API_KEY in "
                    "environment or Django settings."
                )

            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=api_key)
            except ImportError:
                raise EmbeddingError(
                    "OpenAI package not installed. Install with: pip install openai"
                )

        return self._client

    @property
    def model_name(self) -> str:
        """Return the OpenAI model name."""
        return f"openai/{self._model}"

    @property
    def dimensions(self) -> int:
        """Return the embedding dimensions for this model."""
        return self._dimensions

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using OpenAI's API.

        Args:
            texts: A list of strings to embed.

        Returns:
            A list of embedding vectors.

        Raises:
            EmbeddingError: If the API call fails.
        """
        if not texts:
            return []

        # Clean texts - OpenAI doesn't like empty strings
        cleaned_texts = [t.strip() if t else " " for t in texts]

        try:
            client = self._get_client()
            response = client.embeddings.create(
                input=cleaned_texts,
                model=self._model
            )

            # Sort by index to ensure order matches input
            embeddings = sorted(response.data, key=lambda x: x.index)
            result = [e.embedding for e in embeddings]

            logger.debug(
                f"Generated {len(result)} embeddings using {self._model} "
                f"(dimensions={self._dimensions})"
            )
            return result

        except Exception as e:
            logger.error(f"OpenAI embedding failed: {str(e)}")
            raise EmbeddingError(f"Failed to generate OpenAI embeddings: {str(e)}")


class SentenceTransformerEmbedding(BaseEmbedding):
    """
    SentenceTransformers embedding model implementation.

    Uses locally loaded SentenceTransformer models for embedding generation.
    This is the default embedding approach used by the existing ExcelPoint system.

    Attributes:
        model: The SentenceTransformer model instance.

    Supported models include:
        - all-MiniLM-L6-v2 (384 dimensions, fast)
        - all-mpnet-base-v2 (768 dimensions, high quality)
        - multi-qa-MiniLM-L6-cos-v1 (384 dimensions, optimized for QA)
        - And any other model from the SentenceTransformers library
    """

    # Common model configurations: model_name -> dimensions
    # Note: This is not exhaustive, just commonly used models
    KNOWN_DIMENSIONS = {
        'all-MiniLM-L6-v2': 384,
        'all-mpnet-base-v2': 768,
        'multi-qa-MiniLM-L6-cos-v1': 384,
        'paraphrase-MiniLM-L6-v2': 384,
        'all-distilroberta-v1': 768,
        'multi-qa-mpnet-base-dot-v1': 768,
    }

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the SentenceTransformer embedding model.

        Args:
            model_name: The model to load. Defaults to 'all-MiniLM-L6-v2'.

        Raises:
            EmbeddingError: If the model cannot be loaded.
        """
        self._model_name = model_name
        self._model = None
        self._dimensions = None

    def _load_model(self):
        """
        Lazy-load the SentenceTransformer model.

        Returns:
            The loaded SentenceTransformer model.

        Raises:
            EmbeddingError: If the model cannot be loaded.
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer model: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
                # Get actual dimensions from the model
                self._dimensions = self._model.get_sentence_embedding_dimension()
                logger.info(
                    f"Loaded {self._model_name} with {self._dimensions} dimensions"
                )
            except ImportError:
                raise EmbeddingError(
                    "sentence-transformers package not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                raise EmbeddingError(
                    f"Failed to load SentenceTransformer model '{self._model_name}': {str(e)}"
                )

        return self._model

    @property
    def model_name(self) -> str:
        """Return the SentenceTransformer model name."""
        return f"sentence-transformers/{self._model_name}"

    @property
    def dimensions(self) -> int:
        """Return the embedding dimensions for this model."""
        if self._dimensions is None:
            # Return known dimensions or load model to get actual dimensions
            if self._model_name in self.KNOWN_DIMENSIONS:
                return self.KNOWN_DIMENSIONS[self._model_name]
            # Need to load model to get dimensions
            self._load_model()
        return self._dimensions

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using SentenceTransformers.

        Args:
            texts: A list of strings to embed.

        Returns:
            A list of embedding vectors.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        if not texts:
            return []

        try:
            model = self._load_model()

            # Generate embeddings
            embeddings = model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )

            # Convert numpy arrays to lists
            result = [emb.tolist() for emb in embeddings]

            logger.debug(
                f"Generated {len(result)} embeddings using {self._model_name} "
                f"(dimensions={self._dimensions})"
            )
            return result

        except Exception as e:
            logger.error(f"SentenceTransformer embedding failed: {str(e)}")
            raise EmbeddingError(
                f"Failed to generate SentenceTransformer embeddings: {str(e)}"
            )


class EmbeddingFactory:
    """
    Factory class for creating embedding model instances.

    Provides a centralized way to instantiate embedding models by name,
    supporting runtime selection of embedding providers.

    Naming conventions:
        - OpenAI models: 'openai/text-embedding-ada-002', 'openai/text-embedding-3-small'
        - SentenceTransformers: 'sentence-transformers/all-MiniLM-L6-v2' or just 'all-MiniLM-L6-v2'

    Usage:
        model = EmbeddingFactory.get_embedding_model('openai/text-embedding-3-small')
        embeddings = model.embed(["Hello world"])
    """

    # Aliases for common models
    ALIASES = {
        'ada-002': 'openai/text-embedding-ada-002',
        'ada': 'openai/text-embedding-ada-002',
        'text-embedding-ada-002': 'openai/text-embedding-ada-002',
        'text-embedding-3-small': 'openai/text-embedding-3-small',
        'text-embedding-3-large': 'openai/text-embedding-3-large',
        'minilm': 'sentence-transformers/all-MiniLM-L6-v2',
        'all-MiniLM-L6-v2': 'sentence-transformers/all-MiniLM-L6-v2',
        'mpnet': 'sentence-transformers/all-mpnet-base-v2',
        'all-mpnet-base-v2': 'sentence-transformers/all-mpnet-base-v2',
    }

    @classmethod
    def get_embedding_model(cls, model_name: str) -> BaseEmbedding:
        """
        Get an embedding model instance by name.

        Args:
            model_name: The name of the embedding model. Can be:
                - Full name: 'openai/text-embedding-3-small'
                - Alias: 'ada-002', 'minilm'
                - SentenceTransformer model name: 'all-MiniLM-L6-v2'

        Returns:
            A BaseEmbedding instance.

        Raises:
            ValueError: If the model name format is invalid.
            EmbeddingError: If the model cannot be instantiated.
        """
        # Check for aliases first
        if model_name in cls.ALIASES:
            model_name = cls.ALIASES[model_name]

        # Parse provider/model format
        if '/' in model_name:
            provider, model = model_name.split('/', 1)
            provider = provider.lower()
        else:
            # Default to SentenceTransformers for unknown format
            provider = 'sentence-transformers'
            model = model_name

        logger.debug(f"Creating embedding model: provider={provider}, model={model}")

        if provider == 'openai':
            return OpenAIEmbedding(model=model)
        elif provider in ('sentence-transformers', 'st', 'sbert'):
            return SentenceTransformerEmbedding(model_name=model)
        else:
            raise ValueError(
                f"Unknown embedding provider: '{provider}'. "
                f"Supported providers: openai, sentence-transformers"
            )

    @classmethod
    def list_models(cls) -> Dict[str, List[str]]:
        """
        List all known embedding models by provider.

        Returns:
            A dictionary mapping provider names to lists of model names.
        """
        return {
            'openai': list(OpenAIEmbedding.MODEL_CONFIGS.keys()),
            'sentence-transformers': list(SentenceTransformerEmbedding.KNOWN_DIMENSIONS.keys()),
        }

    @classmethod
    def list_aliases(cls) -> Dict[str, str]:
        """
        List all available model aliases.

        Returns:
            A dictionary mapping aliases to full model names.
        """
        return cls.ALIASES.copy()

    @classmethod
    def get_model_info(cls, model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific embedding model.

        Args:
            model_name: The name of the embedding model.

        Returns:
            A dictionary containing model information.
        """
        model = cls.get_embedding_model(model_name)
        return model.get_model_info()
