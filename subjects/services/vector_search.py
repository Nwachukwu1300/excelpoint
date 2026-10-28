"""Vector search service for semantic content retrieval.

This module provides vector-based search capabilities for the Excelpoint
chatbot using sentence transformers. It enables semantic search across
uploaded educational materials by converting text queries and content
chunks into high-dimensional vectors and computing similarity scores.

Key features:
- Sentence transformer model for text encoding
- Cosine similarity calculations for semantic matching
- Subject-scoped search with caching
- Batch processing for multiple queries
- Fallback mechanisms for search failures

The service integrates with the ContentProcessor infrastructure and
provides the foundation for RAG (Retrieval Augmented Generation)
functionality in the chatbot.
"""

import hashlib
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from pgvector.django import CosineDistance
from ..models import EMBEDDING_DIMENSIONS, ContentChunk, Subject
from ..utils import load_embedding_model

logger = logging.getLogger(__name__)


def nearest_chunks(query_embedding, subject_id: int, top_k: int):
    """Return the subject's top_k chunks closest to query_embedding, each annotated with
    `distance` (cosine distance; similarity = 1 - distance). Search runs in Postgres via pgvector."""
    query_embedding = [float(x) for x in query_embedding]
    if len(query_embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Query embedding has {len(query_embedding)} dimensions but stored chunks use "
            f"{EMBEDDING_DIMENSIONS} (all-MiniLM-L6-v2); re-embed the chunks to compare other models"
        )
    with transaction.atomic():
        # HNSW scans a fixed candidate list; iterative scan keeps going until the subject filter yields top_k
        with transaction.get_connection().cursor() as cursor:
            cursor.execute("SET LOCAL hnsw.iterative_scan = 'relaxed_order'")
        return list(
            ContentChunk.objects
            .filter(material__subject_id=subject_id, embedding_vector__isnull=False)
            .select_related('material')
            .annotate(distance=CosineDistance('embedding_vector', query_embedding))
            .order_by('distance')[:top_k]
        )


class VectorSearchService:
    """Enhanced vector search service for semantic content retrieval.
    
    This service provides the core functionality for finding relevant
    content chunks based on semantic similarity to user queries. It
    uses the 'all-MiniLM-L6-v2' sentence transformer model to convert
    text into 384-dimensional vectors and performs cosine similarity
    calculations for ranking results.
    
    The service includes caching for query embeddings, subject-scoped
    search capabilities, and robust error handling for production use.
    """
    
    def __init__(self):
        """Initialize the vector search service with lazy model loading."""
        self.model = None
        self._model_loaded = False
        
    def _ensure_model_loaded(self):
        """Lazy load the sentence transformer model.
        
        Loads the model only when first needed to reduce memory usage
        and startup time. The model is cached for subsequent operations.
        
        Raises:
            Exception: If model loading fails
        """
        if not self._model_loaded:
            try:
                self.model = load_embedding_model()
                self._model_loaded = True
                logger.info("Successfully loaded SentenceTransformer model: all-MiniLM-L6-v2")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model: {str(e)}")
                raise Exception(f"Vector search service initialization failed: {str(e)}")
    
    def encode_query(self, text: str) -> np.ndarray:
        """Encode a text query into a vector embedding.
        
        Converts user queries into high-dimensional vectors for semantic
        comparison with content chunks. Results are cached to improve
        performance for repeated queries.
        
        Args:
            text: The query text to encode
            
        Returns:
            numpy array of the embedding vector (384 dimensions)
            
        Raises:
            ValueError: If query text is empty
            Exception: If encoding fails
        """
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty")
            
        try:
            self._ensure_model_loaded()
            
            # Check cache first
            # hash() is randomised per process, so it never hit across workers
            cache_key = f"query_embedding:{hashlib.md5(text.strip().encode()).hexdigest()}"
            cached_embedding = cache.get(cache_key)
            if cached_embedding is not None:
                return np.array(cached_embedding)
            
            # Generate embedding
            embedding = self.model.encode(text.strip())
            
            # Cache the result (TTL: 1 hour)
            cache.set(cache_key, embedding.tolist(), timeout=3600)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error encoding query '{text[:50]}...': {str(e)}")
            raise Exception(f"Failed to encode query: {str(e)}")
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.
        
        Computes the cosine similarity score between two vectors, which
        measures the cosine of the angle between them. This provides a
        normalized similarity score between 0 (orthogonal) and 1 (identical).
        
        Args:
            vec1: First vector (numpy array)
            vec2: Second vector (numpy array)
            
        Returns:
            Cosine similarity score between 0.0 and 1.0
            
        Raises:
            ValueError: If vectors are invalid or empty
        """
        try:
            # Handle edge cases
            if len(vec1) == 0 or len(vec2) == 0:
                return 0.0
                
            # Ensure vectors are numpy arrays
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            # Check for zero vectors
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            
            # Ensure result is between 0 and 1
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
    
    def cosine_similarity_batch(self, query_embedding: np.ndarray, chunk_embeddings: List[np.ndarray]) -> List[float]:
        """
        Calculate cosine similarities for multiple chunks efficiently using vectorized operations.
        
        Args:
            query_embedding: The query vector
            chunk_embeddings: List of chunk vectors
            
        Returns:
            List of similarity scores
        """
        try:
            if not chunk_embeddings:
                return []
            
            # Convert to numpy array for vectorized operations
            chunk_matrix = np.array(chunk_embeddings)
            query_vec = np.array(query_embedding)
            
            # Calculate norms
            query_norm = np.linalg.norm(query_vec)
            chunk_norms = np.linalg.norm(chunk_matrix, axis=1)
            
            # Handle zero vectors
            if query_norm == 0:
                return [0.0] * len(chunk_embeddings)
            
            # Vectorized dot product
            dot_products = np.dot(chunk_matrix, query_vec)
            
            # Vectorized cosine similarity calculation
            similarities = dot_products / (chunk_norms * query_norm)
            
            # Ensure values are between 0 and 1, handle NaN
            similarities = np.nan_to_num(similarities, nan=0.0)
            similarities = np.clip(similarities, 0.0, 1.0)
            
            return similarities.tolist()
            
        except Exception as e:
            logger.error(f"Error in batch cosine similarity calculation: {str(e)}")
            return [0.0] * len(chunk_embeddings)
    
    def get_subject_chunks(self, subject_id: int) -> List[ContentChunk]:
        """
        Get all content chunks for a specific subject that have embeddings.
        
        Args:
            subject_id: The ID of the subject
            
        Returns:
            List of ContentChunk objects with embeddings
            
        Raises:
            ValueError: If subject doesn't exist
        """
        try:
            # Verify subject exists
            if not Subject.objects.filter(id=subject_id).exists():
                raise ValueError(f"Subject with ID {subject_id} does not exist")
            
            # Get chunks with embeddings for this subject
            chunks = ContentChunk.objects.filter(
                material__subject_id=subject_id,
                embedding_vector__isnull=False
            ).select_related('material').order_by('material_id', 'chunk_index')
            
            chunks_list = list(chunks)
            logger.debug(f"Found {len(chunks_list)} chunks with embeddings for subject {subject_id}")
            
            return chunks_list
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving chunks for subject {subject_id}: {str(e)}")
            raise Exception(f"Failed to retrieve subject chunks: {str(e)}")
    
    def search_similar_chunks(
        self, 
        query_embedding: np.ndarray, 
        subject_id: int, 
        top_k: int = 5, 
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for the most similar chunks to a query embedding within a specific subject.
        
        Args:
            query_embedding: The encoded query vector
            subject_id: ID of the subject to search within
            top_k: Maximum number of chunks to return
            threshold: Minimum similarity score threshold (0.0 to 1.0)
            
        Returns:
            List of dictionaries containing chunk data and similarity scores
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If search fails
        """
        try:
            # Validate parameters
            if top_k <= 0:
                raise ValueError("top_k must be greater than 0")
            if not 0.0 <= threshold <= 1.0:
                raise ValueError("threshold must be between 0.0 and 1.0")
            
            if not Subject.objects.filter(id=subject_id).exists():
                raise ValueError(f"Subject with ID {subject_id} does not exist")

            results = []
            for chunk in nearest_chunks(query_embedding, subject_id, top_k):
                similarity = 1.0 - chunk.distance
                if similarity >= threshold:
                    results.append({
                        'chunk_id': chunk.id,
                        'content': chunk.content,
                        'chunk_index': chunk.chunk_index,
                        'material_id': chunk.material.id,
                        'material_name': chunk.material.display_name,
                        'similarity_score': float(similarity),
                        'metadata': {
                            'material_type': chunk.material.file_type,
                            'created_at': chunk.created_at.isoformat(),
                        }
                    })

            # Sort by similarity score (descending) and limit to top_k
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            final_results = results[:top_k]
            
            logger.info(f"Found {len(final_results)} relevant chunks for subject {subject_id} "
                       f"(threshold: {threshold}, top_k: {top_k})")
            
            return final_results
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error searching similar chunks for subject {subject_id}: {str(e)}")
            raise Exception(f"Vector search failed: {str(e)}")
    
    def search_by_query(
        self, 
        query_text: str, 
        subject_id: int, 
        top_k: int = 5, 
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using a text query.
        
        Args:
            query_text: The search query text
            subject_id: ID of the subject to search within
            top_k: Maximum number of chunks to return
            threshold: Minimum similarity score threshold
            
        Returns:
            List of similar chunks with metadata
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If search fails
        """
        try:
            # Encode the query
            query_embedding = self.encode_query(query_text)
            
            # Search for similar chunks
            return self.search_similar_chunks(query_embedding, subject_id, top_k, threshold)
            
        except Exception as e:
            logger.error(f"Error in query-based search: {str(e)}")
            raise
    
    def get_search_stats(self, subject_id: int) -> Dict[str, Any]:
        """
        Get statistics about the vector search index for a subject.
        
        Args:
            subject_id: ID of the subject
            
        Returns:
            Dictionary with search statistics
        """
        try:
            chunks = self.get_subject_chunks(subject_id)
            
            total_chunks = len(chunks)
            materials = set(chunk.material.id for chunk in chunks)
            
            return {
                'subject_id': subject_id,
                'total_chunks': total_chunks,
                'total_materials': len(materials),
                'has_embeddings': total_chunks > 0,
                'materials_with_chunks': list(materials),
                'embedding_model': 'all-MiniLM-L6-v2'
            }
            
        except Exception as e:
            logger.error(f"Error getting search stats for subject {subject_id}: {str(e)}")
            return {
                'subject_id': subject_id,
                'error': str(e),
                'has_embeddings': False
            } 