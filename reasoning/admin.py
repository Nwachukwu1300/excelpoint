"""
Django admin configuration for the reasoning pipeline.

Registers ReasoningSession and ReasoningSessionChunk models
with the Django admin interface for easy management and debugging.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import ReasoningSession, ReasoningSessionChunk


class ReasoningSessionChunkInline(admin.TabularInline):
    """
    Inline admin for viewing chunks within a session.

    Shows chunks in a compact table format within the session detail view.
    """

    model = ReasoningSessionChunk
    extra = 0
    readonly_fields = [
        'chunk_id',
        'chunk_index',
        'material_id',
        'material_name',
        'similarity_score',
        'reranking_score',
        'used_in_retry',
    ]
    fields = [
        'chunk_id',
        'material_name',
        'chunk_index',
        'similarity_score',
        'reranking_score',
        'used_in_retry',
    ]
    can_delete = False
    max_num = 0  # Don't allow adding new chunks

    def has_add_permission(self, request, obj=None):
        """Disable adding chunks through admin."""
        return False


@admin.register(ReasoningSession)
class ReasoningSessionAdmin(admin.ModelAdmin):
    """
    Admin configuration for ReasoningSession model.

    Provides list view, filtering, searching, and detail editing
    for reasoning sessions.
    """

    list_display = [
        'session_id_short',
        'query_preview',
        'classification_category',
        'confidence_display',
        'verification_status',
        'retry_count',
        'latency_display',
        'created_at',
    ]
    list_filter = [
        'classification_category',
        'confidence_interpretation',
        'unverified',
        'pipeline_name',
        'created_at',
    ]
    search_fields = [
        'session_id',
        'original_query',
        'final_answer',
        'pipeline_name',
    ]
    readonly_fields = [
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
        'full_result',
        'subject_id',
        'created_at',
    ]
    fieldsets = [
        ('Session Info', {
            'fields': ['session_id', 'subject_id', 'created_at']
        }),
        ('Query', {
            'fields': [
                'original_query',
                'classification_category',
                'rewritten_query',
            ]
        }),
        ('Retrieval', {
            'fields': ['pipeline_name', 'retrieved_chunk_count']
        }),
        ('Answers', {
            'fields': ['generated_answer', 'final_answer']
        }),
        ('Verification', {
            'fields': [
                'faithfulness_score',
                'confidence_score',
                'confidence_interpretation',
                'unverified',
                'retry_count',
            ]
        }),
        ('Performance', {
            'fields': ['total_latency', 'latency_breakdown'],
            'classes': ['collapse'],
        }),
        ('Full Result (JSON)', {
            'fields': ['full_result'],
            'classes': ['collapse'],
        }),
    ]
    inlines = [ReasoningSessionChunkInline]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def session_id_short(self, obj: ReasoningSession) -> str:
        """Display shortened session ID."""
        return str(obj.session_id)[:8] + '...'
    session_id_short.short_description = 'Session ID'

    def query_preview(self, obj: ReasoningSession) -> str:
        """Display truncated query."""
        query = obj.original_query
        if len(query) > 50:
            return query[:50] + '...'
        return query
    query_preview.short_description = 'Query'

    def confidence_display(self, obj: ReasoningSession) -> str:
        """Display confidence score with color coding."""
        if obj.confidence_score is None:
            return '-'

        score = obj.confidence_score
        if score >= 0.8:
            color = 'green'
        elif score >= 0.5:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {};">{:.2f} ({})</span>',
            color,
            score,
            obj.confidence_interpretation[:3] if obj.confidence_interpretation else '?'
        )
    confidence_display.short_description = 'Confidence'

    def verification_status(self, obj: ReasoningSession) -> str:
        """Display verification status with icon."""
        if obj.unverified:
            return format_html(
                '<span style="color: red;">Unverified</span>'
            )
        return format_html(
            '<span style="color: green;">Verified</span>'
        )
    verification_status.short_description = 'Status'

    def latency_display(self, obj: ReasoningSession) -> str:
        """Display latency in human-readable format."""
        latency = obj.total_latency
        if latency >= 1000:
            return f'{latency / 1000:.2f}s'
        return f'{latency:.0f}ms'
    latency_display.short_description = 'Latency'


@admin.register(ReasoningSessionChunk)
class ReasoningSessionChunkAdmin(admin.ModelAdmin):
    """
    Admin configuration for ReasoningSessionChunk model.

    Provides list view and detail viewing for individual chunks.
    """

    list_display = [
        'id',
        'session_short',
        'material_name',
        'chunk_index',
        'similarity_score',
        'reranking_score',
        'used_in_retry',
    ]
    list_filter = [
        'used_in_retry',
        'material_name',
    ]
    search_fields = [
        'chunk_text',
        'material_name',
        'session__session_id',
    ]
    readonly_fields = [
        'session',
        'chunk_id',
        'chunk_text',
        'chunk_index',
        'material_id',
        'material_name',
        'similarity_score',
        'reranking_score',
        'used_in_retry',
    ]
    ordering = ['-session__created_at', '-similarity_score']

    def session_short(self, obj: ReasoningSessionChunk) -> str:
        """Display shortened session ID."""
        return str(obj.session.session_id)[:8] + '...'
    session_short.short_description = 'Session'

    def has_add_permission(self, request):
        """Disable adding chunks through admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing chunks through admin."""
        return False
