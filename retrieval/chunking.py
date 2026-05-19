"""
Chunking strategies for content segmentation.

This module provides multiple text chunking strategies that can be swapped
based on use case requirements. All chunkers implement a common interface
returning standardized chunk metadata.

Supported strategies:
- FixedSizeChunker: Split by character count with no overlap
- OverlapChunker: Split with configurable overlap between chunks
- SemanticChunker: Split at natural boundaries (sentences/paragraphs)

Usage:
    from retrieval.chunking import ChunkingFactory

    chunker = ChunkingFactory.get_chunker('fixed_size', chunk_size=500)
    chunks = chunker.chunk("Your long text here...")
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    Represents a single chunk of text with metadata.

    Attributes:
        text: The actual text content of the chunk.
        index: The zero-based position of this chunk in the sequence.
        start_pos: The starting character position in the original text.
        end_pos: The ending character position in the original text.
        strategy_name: The name of the chunking strategy that produced this chunk.
    """
    text: str
    index: int
    start_pos: int
    end_pos: int
    strategy_name: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert the chunk to a dictionary representation."""
        return asdict(self)


class BaseChunker(ABC):
    """
    Abstract base class for all chunking strategies.

    All chunkers must implement the chunk() method which takes a text string
    and returns a list of Chunk objects with consistent metadata.
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the name of this chunking strategy."""
        pass

    @abstractmethod
    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text into chunks.

        Args:
            text: The input text to be chunked.

        Returns:
            A list of Chunk objects containing the segmented text with metadata.
        """
        pass

    def _clean_text(self, text: str) -> str:
        """
        Clean text by removing null characters and normalizing whitespace.

        Args:
            text: The input text to clean.

        Returns:
            Cleaned text with normalized whitespace.
        """
        # Remove null characters
        text = text.replace('\x00', '')
        # Remove other control characters except newlines and tabs
        text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Normalize multiple spaces to single space (preserve newlines)
        text = re.sub(r'[^\S\n]+', ' ', text)
        return text.strip()


class FixedSizeChunker(BaseChunker):
    """
    Split text into fixed-size chunks with no overlap.

    This is the simplest chunking strategy. It divides text into chunks
    of exactly the specified character count (except possibly the last chunk).

    Attributes:
        chunk_size: The number of characters per chunk.
    """

    def __init__(self, chunk_size: int = 1000):
        """
        Initialize the fixed-size chunker.

        Args:
            chunk_size: The number of characters per chunk. Defaults to 1000.

        Raises:
            ValueError: If chunk_size is less than 1.
        """
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1")
        self._chunk_size = chunk_size

    @property
    def strategy_name(self) -> str:
        """Return the strategy name."""
        return "fixed_size"

    @property
    def chunk_size(self) -> int:
        """Return the configured chunk size."""
        return self._chunk_size

    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text into fixed-size chunks.

        Args:
            text: The input text to be chunked.

        Returns:
            A list of Chunk objects, each containing up to chunk_size characters.
        """
        if not text:
            logger.debug("Empty text provided to FixedSizeChunker")
            return []

        cleaned_text = self._clean_text(text)
        if not cleaned_text:
            logger.debug("Text is empty after cleaning")
            return []

        chunks = []
        index = 0
        start_pos = 0

        while start_pos < len(cleaned_text):
            end_pos = min(start_pos + self._chunk_size, len(cleaned_text))
            chunk_text = cleaned_text[start_pos:end_pos]

            chunks.append(Chunk(
                text=chunk_text,
                index=index,
                start_pos=start_pos,
                end_pos=end_pos,
                strategy_name=self.strategy_name
            ))

            start_pos = end_pos
            index += 1

        logger.debug(f"FixedSizeChunker produced {len(chunks)} chunks from {len(cleaned_text)} characters")
        return chunks


class OverlapChunker(BaseChunker):
    """
    Split text into overlapping chunks.

    This strategy creates chunks that overlap with each other, which can
    help preserve context across chunk boundaries. Useful when semantic
    meaning might be split at arbitrary character boundaries.

    Attributes:
        chunk_size: The number of characters per chunk.
        overlap_size: The number of characters that overlap between consecutive chunks.
    """

    def __init__(self, chunk_size: int = 1000, overlap_size: int = 200):
        """
        Initialize the overlap chunker.

        Args:
            chunk_size: The number of characters per chunk. Defaults to 1000.
            overlap_size: The number of overlapping characters. Defaults to 200.

        Raises:
            ValueError: If chunk_size < 1 or overlap_size >= chunk_size or overlap_size < 0.
        """
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1")
        if overlap_size < 0:
            raise ValueError("overlap_size must be non-negative")
        if overlap_size >= chunk_size:
            raise ValueError("overlap_size must be less than chunk_size")

        self._chunk_size = chunk_size
        self._overlap_size = overlap_size

    @property
    def strategy_name(self) -> str:
        """Return the strategy name."""
        return "overlap"

    @property
    def chunk_size(self) -> int:
        """Return the configured chunk size."""
        return self._chunk_size

    @property
    def overlap_size(self) -> int:
        """Return the configured overlap size."""
        return self._overlap_size

    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text into overlapping chunks.

        Args:
            text: The input text to be chunked.

        Returns:
            A list of Chunk objects with overlapping content between consecutive chunks.
        """
        if not text:
            logger.debug("Empty text provided to OverlapChunker")
            return []

        cleaned_text = self._clean_text(text)
        if not cleaned_text:
            logger.debug("Text is empty after cleaning")
            return []

        chunks = []
        index = 0
        start_pos = 0
        step_size = self._chunk_size - self._overlap_size

        while start_pos < len(cleaned_text):
            end_pos = min(start_pos + self._chunk_size, len(cleaned_text))
            chunk_text = cleaned_text[start_pos:end_pos]

            chunks.append(Chunk(
                text=chunk_text,
                index=index,
                start_pos=start_pos,
                end_pos=end_pos,
                strategy_name=self.strategy_name
            ))

            # Move forward by step_size (chunk_size - overlap_size)
            start_pos += step_size
            index += 1

            # Prevent infinite loop if we're at the end
            if start_pos >= len(cleaned_text):
                break

        logger.debug(
            f"OverlapChunker produced {len(chunks)} chunks from {len(cleaned_text)} characters "
            f"(chunk_size={self._chunk_size}, overlap={self._overlap_size})"
        )
        return chunks


class SemanticChunker(BaseChunker):
    """
    Split text at natural semantic boundaries.

    This strategy respects sentence and paragraph boundaries, grouping
    sentences into chunks that stay within a token/character limit.
    This produces more meaningful chunks that don't break mid-sentence.

    The chunker prioritizes:
    1. Paragraph breaks (double newlines)
    2. Sentence endings (., !, ?)
    3. Other natural breaks (single newlines, semicolons)

    Attributes:
        max_tokens: Approximate maximum tokens per chunk.
        chars_per_token: Estimated characters per token (default 4).
    """

    # Sentence ending pattern
    SENTENCE_ENDINGS = re.compile(r'(?<=[.!?])\s+')
    # Paragraph break pattern
    PARAGRAPH_BREAKS = re.compile(r'\n\s*\n')

    def __init__(self, max_tokens: int = 256, chars_per_token: float = 4.0):
        """
        Initialize the semantic chunker.

        Args:
            max_tokens: Approximate maximum tokens per chunk. Defaults to 256.
            chars_per_token: Estimated characters per token. Defaults to 4.0.

        Raises:
            ValueError: If max_tokens < 1 or chars_per_token <= 0.
        """
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        if chars_per_token <= 0:
            raise ValueError("chars_per_token must be positive")

        self._max_tokens = max_tokens
        self._chars_per_token = chars_per_token
        self._max_chars = int(max_tokens * chars_per_token)

    @property
    def strategy_name(self) -> str:
        """Return the strategy name."""
        return "semantic"

    @property
    def max_tokens(self) -> int:
        """Return the configured maximum tokens."""
        return self._max_tokens

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: The input text.

        Returns:
            A list of sentences.
        """
        # First split by paragraphs
        paragraphs = self.PARAGRAPH_BREAKS.split(text)
        sentences = []

        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            # Split paragraph into sentences
            para_sentences = self.SENTENCE_ENDINGS.split(paragraph)
            for sent in para_sentences:
                sent = sent.strip()
                if sent:
                    sentences.append(sent)

        return sentences

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in text.

        Args:
            text: The input text.

        Returns:
            Estimated token count.
        """
        return int(len(text) / self._chars_per_token)

    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text at semantic boundaries.

        Groups sentences into chunks that stay within the token limit,
        respecting natural language boundaries.

        Args:
            text: The input text to be chunked.

        Returns:
            A list of Chunk objects split at semantic boundaries.
        """
        if not text:
            logger.debug("Empty text provided to SemanticChunker")
            return []

        cleaned_text = self._clean_text(text)
        if not cleaned_text:
            logger.debug("Text is empty after cleaning")
            return []

        sentences = self._split_into_sentences(cleaned_text)
        if not sentences:
            # If no sentences found, fall back to the whole text as one chunk
            return [Chunk(
                text=cleaned_text,
                index=0,
                start_pos=0,
                end_pos=len(cleaned_text),
                strategy_name=self.strategy_name
            )]

        chunks = []
        current_chunk_sentences = []
        current_chunk_chars = 0
        index = 0

        # Track position in original text
        current_pos = 0

        for sentence in sentences:
            sentence_chars = len(sentence)

            # If adding this sentence would exceed the limit
            if current_chunk_chars + sentence_chars > self._max_chars and current_chunk_sentences:
                # Finalize current chunk
                chunk_text = ' '.join(current_chunk_sentences)
                start_pos = cleaned_text.find(current_chunk_sentences[0], current_pos)
                if start_pos == -1:
                    start_pos = current_pos
                end_pos = start_pos + len(chunk_text)

                chunks.append(Chunk(
                    text=chunk_text,
                    index=index,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    strategy_name=self.strategy_name
                ))

                current_pos = end_pos
                index += 1
                current_chunk_sentences = []
                current_chunk_chars = 0

            # Handle case where single sentence exceeds limit
            if sentence_chars > self._max_chars and not current_chunk_sentences:
                # Split long sentence into smaller chunks
                words = sentence.split()
                temp_chunk = []
                temp_chars = 0

                for word in words:
                    word_len = len(word) + 1  # +1 for space
                    if temp_chars + word_len > self._max_chars and temp_chunk:
                        chunk_text = ' '.join(temp_chunk)
                        start_pos = cleaned_text.find(temp_chunk[0], current_pos)
                        if start_pos == -1:
                            start_pos = current_pos
                        end_pos = start_pos + len(chunk_text)

                        chunks.append(Chunk(
                            text=chunk_text,
                            index=index,
                            start_pos=start_pos,
                            end_pos=end_pos,
                            strategy_name=self.strategy_name
                        ))

                        current_pos = end_pos
                        index += 1
                        temp_chunk = []
                        temp_chars = 0

                    temp_chunk.append(word)
                    temp_chars += word_len

                # Add remaining words to current chunk
                if temp_chunk:
                    current_chunk_sentences.append(' '.join(temp_chunk))
                    current_chunk_chars += temp_chars
            else:
                current_chunk_sentences.append(sentence)
                current_chunk_chars += sentence_chars + 1  # +1 for space

        # Finalize last chunk
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            start_pos = cleaned_text.find(current_chunk_sentences[0], current_pos)
            if start_pos == -1:
                start_pos = current_pos
            end_pos = min(start_pos + len(chunk_text), len(cleaned_text))

            chunks.append(Chunk(
                text=chunk_text,
                index=index,
                start_pos=start_pos,
                end_pos=end_pos,
                strategy_name=self.strategy_name
            ))

        logger.debug(
            f"SemanticChunker produced {len(chunks)} chunks from {len(cleaned_text)} characters "
            f"(max_tokens={self._max_tokens})"
        )
        return chunks


class ChunkingFactory:
    """
    Factory class for creating chunker instances.

    Provides a centralized way to instantiate chunkers by strategy name,
    supporting runtime selection of chunking strategies.

    Supported strategies:
        - 'fixed_size': FixedSizeChunker
        - 'overlap': OverlapChunker
        - 'semantic': SemanticChunker

    Usage:
        chunker = ChunkingFactory.get_chunker('overlap', chunk_size=500, overlap_size=100)
        chunks = chunker.chunk("Your text here")
    """

    STRATEGIES = {
        'fixed_size': FixedSizeChunker,
        'overlap': OverlapChunker,
        'semantic': SemanticChunker,
    }

    @classmethod
    def get_chunker(cls, strategy: str, **kwargs) -> BaseChunker:
        """
        Get a chunker instance for the specified strategy.

        Args:
            strategy: The name of the chunking strategy.
            **kwargs: Strategy-specific parameters.
                - fixed_size: chunk_size (int)
                - overlap: chunk_size (int), overlap_size (int)
                - semantic: max_tokens (int), chars_per_token (float)

        Returns:
            A BaseChunker instance configured with the provided parameters.

        Raises:
            ValueError: If the strategy name is not recognized.
        """
        strategy = strategy.lower().strip()

        if strategy not in cls.STRATEGIES:
            available = ', '.join(cls.STRATEGIES.keys())
            raise ValueError(
                f"Unknown chunking strategy: '{strategy}'. "
                f"Available strategies: {available}"
            )

        chunker_class = cls.STRATEGIES[strategy]
        logger.debug(f"Creating {strategy} chunker with params: {kwargs}")

        try:
            return chunker_class(**kwargs)
        except TypeError as e:
            raise ValueError(f"Invalid parameters for {strategy} chunker: {e}")

    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        List all available chunking strategies.

        Returns:
            A list of strategy names.
        """
        return list(cls.STRATEGIES.keys())

    @classmethod
    def get_strategy_info(cls, strategy: str) -> Dict[str, Any]:
        """
        Get information about a specific chunking strategy.

        Args:
            strategy: The name of the chunking strategy.

        Returns:
            A dictionary containing strategy information including:
            - name: The strategy name
            - description: The strategy's docstring
            - parameters: Expected parameters

        Raises:
            ValueError: If the strategy name is not recognized.
        """
        strategy = strategy.lower().strip()

        if strategy not in cls.STRATEGIES:
            available = ', '.join(cls.STRATEGIES.keys())
            raise ValueError(
                f"Unknown chunking strategy: '{strategy}'. "
                f"Available strategies: {available}"
            )

        chunker_class = cls.STRATEGIES[strategy]

        # Extract parameter info from __init__ signature
        import inspect
        sig = inspect.signature(chunker_class.__init__)
        params = {
            name: {
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'required': param.default == inspect.Parameter.empty
            }
            for name, param in sig.parameters.items()
            if name != 'self'
        }

        return {
            'name': strategy,
            'description': chunker_class.__doc__,
            'parameters': params
        }
