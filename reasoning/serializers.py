"""
DRF serializers for the reasoning API.

Provides serializers for:
- Model serialization (ReasoningSession, ReasoningSessionChunk)
- Request validation (QueryInput, SessionFilter)
- Response formatting (QueryResponse, StatsResponse)
"""

from rest_framework import serializers

from .models import ReasoningSession, ReasoningSessionChunk


# =============================================================================
# Model Serializers
# =============================================================================

class ReasoningSessionChunkSerializer(serializers.ModelSerializer):
    """
    Serializer for ReasoningSessionChunk model.

    Serializes all chunk fields for API responses.
    """

    class Meta:
        model = ReasoningSessionChunk
        fields = [
            'id',
            'chunk_id',
            'chunk_text',
            'chunk_index',
            'material_id',
            'material_name',
            'similarity_score',
            'reranking_score',
            'used_in_retry',
        ]
        read_only_fields = fields


class ReasoningSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for ReasoningSession model.

    Provides a summary view of the session without the full result JSON.
    """

    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = ReasoningSession
        fields = [
            'id',
            'session_id',
            'original_query',
            'classification_category',
            'rewritten_query',
            'pipeline_name',
            'retrieved_chunk_count',
            'generated_answer',
            'final_answer',
            'faithfulness_score',
            'confidence_score',
            'confidence_interpretation',
            'unverified',
            'retry_count',
            'total_latency',
            'latency_breakdown',
            'subject_id',
            'created_at',
            'chunk_count',
        ]
        read_only_fields = fields

    def get_chunk_count(self, obj: ReasoningSession) -> int:
        """Get the count of chunks associated with this session."""
        return obj.chunks.count()


class ReasoningSessionDetailSerializer(ReasoningSessionSerializer):
    """
    Detailed serializer including full result and nested chunks.

    Use this for single session retrieval endpoints.
    """

    chunks = ReasoningSessionChunkSerializer(many=True, read_only=True)

    class Meta(ReasoningSessionSerializer.Meta):
        fields = ReasoningSessionSerializer.Meta.fields + ['full_result', 'chunks']


class ReasoningSessionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for session lists.

    Excludes large fields like generated_answer and full_result for efficiency.
    """

    class Meta:
        model = ReasoningSession
        fields = [
            'id',
            'session_id',
            'original_query',
            'classification_category',
            'pipeline_name',
            'confidence_score',
            'confidence_interpretation',
            'unverified',
            'retry_count',
            'total_latency',
            'subject_id',
            'created_at',
        ]
        read_only_fields = fields


# =============================================================================
# Request Serializers
# =============================================================================

class QueryInputSerializer(serializers.Serializer):
    """
    Serializer for query execution input.

    Validates incoming requests to the /api/reasoning/query/ endpoint.
    """

    query = serializers.CharField(
        min_length=1,
        max_length=5000,
        help_text="The user's query"
    )
    subject_id = serializers.IntegerField(
        min_value=1,
        help_text="Subject ID to search within"
    )
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Previous conversation exchanges as list of {role, content} dicts"
    )
    pipeline_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Retrieval pipeline to use (optional)"
    )

    def validate_query(self, value: str) -> str:
        """Validate and clean the query."""
        return value.strip()

    def validate_conversation_history(self, value: list) -> list:
        """Validate conversation history format."""
        if not value:
            return []

        for i, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    f"Item {i} must be a dictionary with 'role' and 'content' keys"
                )
            if 'role' not in item or 'content' not in item:
                raise serializers.ValidationError(
                    f"Item {i} must have 'role' and 'content' keys"
                )
        return value


class SessionFilterSerializer(serializers.Serializer):
    """
    Serializer for session list filtering.

    Validates query parameters for the session list endpoint.
    """

    pipeline_name = serializers.CharField(required=False, allow_blank=True)
    classification_category = serializers.CharField(required=False, allow_blank=True)
    confidence_min = serializers.FloatField(
        required=False,
        min_value=0,
        max_value=1
    )
    confidence_max = serializers.FloatField(
        required=False,
        min_value=0,
        max_value=1
    )
    confidence_interpretation = serializers.ChoiceField(
        required=False,
        choices=['HIGH_CONFIDENCE', 'MODERATE_CONFIDENCE', 'LOW_CONFIDENCE']
    )
    unverified = serializers.BooleanField(required=False, allow_null=True)
    subject_id = serializers.IntegerField(required=False, min_value=1)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    limit = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        max_value=1000
    )
    offset = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0
    )


# =============================================================================
# Response Serializers
# =============================================================================

class QueryResponseSerializer(serializers.Serializer):
    """
    Serializer for query response.

    Formats the response from the reasoning pipeline for API output.
    """

    session_id = serializers.UUIDField()
    original_query = serializers.CharField()
    classification_category = serializers.CharField()
    rewritten_query = serializers.CharField(allow_null=True)
    pipeline_name = serializers.CharField()
    final_answer = serializers.CharField()
    confidence_score = serializers.FloatField()
    confidence_interpretation = serializers.CharField()
    unverified = serializers.BooleanField()
    retry_count = serializers.IntegerField()
    total_latency_ms = serializers.FloatField()
    retrieved_chunk_count = serializers.IntegerField()
    faithfulness_score = serializers.FloatField(allow_null=True)

    # Optional detailed fields
    generated_answer = serializers.CharField(required=False)
    latency_breakdown = serializers.DictField(required=False)
    verification_reasoning = serializers.CharField(required=False, allow_null=True)


class StatsResponseSerializer(serializers.Serializer):
    """
    Serializer for aggregated statistics response.

    Formats aggregate stats for the /api/reasoning/stats/ endpoint.
    """

    total_sessions = serializers.IntegerField()
    avg_confidence_score = serializers.FloatField(allow_null=True)
    avg_faithfulness_score = serializers.FloatField(allow_null=True)
    avg_latency_ms = serializers.FloatField(allow_null=True)
    classification_breakdown = serializers.DictField(
        child=serializers.IntegerField()
    )
    confidence_breakdown = serializers.DictField(
        child=serializers.IntegerField()
    )
    unverified_rate = serializers.FloatField()
    avg_retry_count = serializers.FloatField(allow_null=True)
    retry_rate = serializers.FloatField()
    date_range = serializers.DictField(required=False)


class ChunkResponseSerializer(serializers.Serializer):
    """
    Serializer for chunk list response.

    Formats chunks for the session chunks endpoint.
    """

    session_id = serializers.UUIDField()
    total_chunks = serializers.IntegerField()
    initial_chunks = serializers.IntegerField()
    retry_chunks = serializers.IntegerField()
    chunks = ReasoningSessionChunkSerializer(many=True)


# =============================================================================
# Nested Result Serializers (for full_result JSON)
# =============================================================================

class ClassificationResultSerializer(serializers.Serializer):
    """Serializer for ClassificationResult within full_result."""

    original_query = serializers.CharField()
    category = serializers.CharField()
    reasoning = serializers.CharField()
    latency_ms = serializers.FloatField()


class RewriteResultSerializer(serializers.Serializer):
    """Serializer for RewriteResult within full_result."""

    original_query = serializers.CharField()
    rewritten_query = serializers.CharField()
    changes_made = serializers.ListField(child=serializers.CharField())
    latency_ms = serializers.FloatField()


class VerificationResultSerializer(serializers.Serializer):
    """Serializer for VerificationResult within full_result."""

    grounded = serializers.BooleanField()
    supported_claims = serializers.ListField(child=serializers.CharField())
    unsupported_claims = serializers.ListField(child=serializers.CharField())
    faithfulness_score = serializers.FloatField()
    reasoning = serializers.CharField()
    latency_ms = serializers.FloatField()


class ConfidenceScoreSerializer(serializers.Serializer):
    """Serializer for ConfidenceScore within full_result."""

    final_score = serializers.FloatField()
    score_breakdown = serializers.DictField(child=serializers.FloatField())
    interpretation = serializers.CharField()


class RetryResultSerializer(serializers.Serializer):
    """Serializer for RetryResult within full_result."""

    attempt_number = serializers.IntegerField()
    rewritten_query = serializers.CharField()
    retrieved_chunk_count = serializers.IntegerField()
    generated_answer = serializers.CharField()
    success = serializers.BooleanField()
    rewrite_strategy = serializers.CharField()


class FullReasoningResultSerializer(serializers.Serializer):
    """
    Serializer for the complete ReasoningResult.

    Used to serialize the full_result JSON field.
    """

    original_query = serializers.CharField()
    subject_id = serializers.IntegerField()
    classification_result = ClassificationResultSerializer(allow_null=True)
    rewritten_query = serializers.CharField(allow_null=True)
    rewrite_result = RewriteResultSerializer(allow_null=True)
    pipeline_name = serializers.CharField()
    retrieved_chunk_count = serializers.IntegerField()
    generated_answer = serializers.CharField()
    verification_result = VerificationResultSerializer(allow_null=True)
    retry_results = RetryResultSerializer(many=True, required=False)
    retry_count = serializers.IntegerField()
    final_answer = serializers.CharField()
    confidence_score = ConfidenceScoreSerializer(allow_null=True)
    unverified_flag = serializers.BooleanField()
    total_latency_ms = serializers.FloatField()
    latency_breakdown = serializers.DictField()
