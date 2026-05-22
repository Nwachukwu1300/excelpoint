"""
Django models for the reasoning pipeline.

Stores reasoning sessions and their associated chunks for
analytics, debugging, and historical analysis.
"""

import uuid

from django.db import models
from django.utils import timezone


class ReasoningSession(models.Model):
    """
    Stores a complete reasoning session with all metadata.

    A reasoning session represents a single query processed through
    the reasoning pipeline, including classification, rewriting,
    retrieval, generation, verification, and confidence scoring.

    Attributes:
        session_id: Unique UUID for this session.
        original_query: The user's original query.
        classification_category: Query classification result.
        rewritten_query: The rewritten query (if applicable).
        pipeline_name: The retrieval pipeline used.
        retrieved_chunk_count: Number of chunks retrieved.
        generated_answer: The initial generated answer.
        final_answer: The final answer after verification/retries.
        faithfulness_score: Score from verification.
        confidence_score: Final confidence score.
        confidence_interpretation: HIGH/MODERATE/LOW.
        unverified: Whether answer could not be verified.
        retry_count: Number of retry attempts.
        total_latency: Total execution time in ms.
        latency_breakdown: JSON breakdown of latencies.
        full_result: Complete ReasoningResult as JSON.
        subject_id: The subject ID that was searched.
        created_at: Session creation timestamp.
    """

    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text="Unique session identifier"
    )
    original_query = models.TextField(
        help_text="The user's original query"
    )
    classification_category = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Query classification category"
    )
    rewritten_query = models.TextField(
        null=True,
        blank=True,
        help_text="The rewritten query for retrieval"
    )
    pipeline_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Retrieval pipeline used"
    )
    retrieved_chunk_count = models.IntegerField(
        default=0,
        help_text="Number of chunks retrieved"
    )
    generated_answer = models.TextField(
        help_text="The initial generated answer"
    )
    final_answer = models.TextField(
        help_text="The final answer after verification"
    )
    faithfulness_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Verification faithfulness score (0-1)"
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Final confidence score (0-1)"
    )
    confidence_interpretation = models.CharField(
        max_length=20,
        default='',
        db_index=True,
        help_text="Confidence interpretation (HIGH_CONFIDENCE/MODERATE_CONFIDENCE/LOW_CONFIDENCE)"
    )
    unverified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether answer could not be verified"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts"
    )
    total_latency = models.FloatField(
        help_text="Total execution time in milliseconds"
    )
    latency_breakdown = models.JSONField(
        default=dict,
        help_text="Breakdown of latencies by stage"
    )
    full_result = models.JSONField(
        default=dict,
        help_text="Complete ReasoningResult as JSON"
    )
    subject_id = models.IntegerField(
        db_index=True,
        help_text="Subject ID that was searched"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Session creation timestamp"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Reasoning Session'
        verbose_name_plural = 'Reasoning Sessions'
        indexes = [
            models.Index(
                fields=['pipeline_name', 'created_at'],
                name='reasoning_pipe_created_idx'
            ),
            models.Index(
                fields=['confidence_score', 'created_at'],
                name='reasoning_conf_created_idx'
            ),
            models.Index(
                fields=['classification_category', 'created_at'],
                name='reasoning_class_created_idx'
            ),
            models.Index(
                fields=['subject_id', 'created_at'],
                name='reasoning_subj_created_idx'
            ),
            models.Index(
                fields=['unverified', 'created_at'],
                name='reasoning_unverif_created_idx'
            ),
        ]

    def __str__(self) -> str:
        """Return string representation."""
        query_preview = self.original_query[:50]
        if len(self.original_query) > 50:
            query_preview += '...'
        return f"Session {self.session_id} - {query_preview}"

    @classmethod
    def create_from_result(cls, result: 'ReasoningResult') -> 'ReasoningSession':
        """
        Create a ReasoningSession from a ReasoningResult.

        Args:
            result: The ReasoningResult to persist.

        Returns:
            The created ReasoningSession instance.
        """
        session = cls(
            original_query=result.original_query,
            classification_category=(
                result.classification_result.category.value
                if result.classification_result else 'unknown'
            ),
            rewritten_query=result.rewritten_query,
            pipeline_name=result.pipeline_name,
            retrieved_chunk_count=len(result.retrieved_chunks),
            generated_answer=result.generated_answer,
            final_answer=result.final_answer,
            faithfulness_score=(
                result.verification_result.faithfulness_score
                if result.verification_result else None
            ),
            confidence_score=(
                result.confidence_score.final_score
                if result.confidence_score else None
            ),
            confidence_interpretation=(
                result.confidence_score.interpretation
                if result.confidence_score else ''
            ),
            unverified=result.unverified_flag,
            retry_count=len(result.retry_results),
            total_latency=result.total_latency_ms,
            latency_breakdown=result.latency_breakdown,
            full_result=result.to_dict(),
            subject_id=result.subject_id,
        )
        session.save()

        # Create chunk records
        for chunk in result.retrieved_chunks:
            ReasoningSessionChunk.objects.create(
                session=session,
                chunk_id=chunk.chunk_id if hasattr(chunk, 'chunk_id') else 0,
                chunk_text=chunk.content if hasattr(chunk, 'content') else str(chunk),
                chunk_index=chunk.chunk_index if hasattr(chunk, 'chunk_index') else 0,
                material_id=chunk.material_id if hasattr(chunk, 'material_id') else 0,
                material_name=chunk.material_name if hasattr(chunk, 'material_name') else '',
                similarity_score=chunk.initial_score if hasattr(chunk, 'initial_score') else 0.0,
                reranking_score=chunk.reranked_score if hasattr(chunk, 'reranked_score') else None,
                used_in_retry=False,
            )

        # Create chunk records for retry attempts
        for retry in result.retry_results:
            for chunk in retry.retrieved_chunks:
                ReasoningSessionChunk.objects.create(
                    session=session,
                    chunk_id=chunk.chunk_id if hasattr(chunk, 'chunk_id') else 0,
                    chunk_text=chunk.content if hasattr(chunk, 'content') else str(chunk),
                    chunk_index=chunk.chunk_index if hasattr(chunk, 'chunk_index') else 0,
                    material_id=chunk.material_id if hasattr(chunk, 'material_id') else 0,
                    material_name=chunk.material_name if hasattr(chunk, 'material_name') else '',
                    similarity_score=chunk.initial_score if hasattr(chunk, 'initial_score') else 0.0,
                    reranking_score=chunk.reranked_score if hasattr(chunk, 'reranked_score') else None,
                    used_in_retry=True,
                )

        return session


class ReasoningSessionChunk(models.Model):
    """
    Stores chunks associated with a reasoning session.

    Each chunk represents a piece of content retrieved from the
    document store during the reasoning process.

    Attributes:
        session: Foreign key to parent session.
        chunk_id: Original chunk ID from retrieval.
        chunk_text: The chunk content.
        chunk_index: Position in the original document.
        material_id: Source material ID.
        material_name: Source material name.
        similarity_score: Initial similarity score.
        reranking_score: Score after reranking (if applied).
        used_in_retry: Whether this chunk was used in a retry.
    """

    session = models.ForeignKey(
        ReasoningSession,
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text="Parent reasoning session"
    )
    chunk_id = models.IntegerField(
        help_text="Original chunk ID from retrieval"
    )
    chunk_text = models.TextField(
        help_text="The chunk content"
    )
    chunk_index = models.IntegerField(
        help_text="Position in original document"
    )
    material_id = models.IntegerField(
        help_text="Source material ID"
    )
    material_name = models.CharField(
        max_length=255,
        help_text="Source material name"
    )
    similarity_score = models.FloatField(
        help_text="Initial similarity score"
    )
    reranking_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Score after reranking"
    )
    used_in_retry = models.BooleanField(
        default=False,
        help_text="Whether chunk was used in a retry attempt"
    )

    class Meta:
        ordering = ['-similarity_score']
        verbose_name = 'Reasoning Session Chunk'
        verbose_name_plural = 'Reasoning Session Chunks'

    def __str__(self) -> str:
        """Return string representation."""
        return f"Chunk {self.chunk_id} for session {self.session.session_id}"
