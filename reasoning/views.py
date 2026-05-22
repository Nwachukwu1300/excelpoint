"""
API views for the reasoning pipeline.

Provides REST API endpoints for:
- Running queries through the reasoning pipeline
- Listing and retrieving reasoning sessions
- Getting session chunks
- Viewing aggregate statistics
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg, Count, Q, Min, Max
from django.utils import timezone

from .models import ReasoningSession, ReasoningSessionChunk
from .serializers import (
    QueryInputSerializer,
    QueryResponseSerializer,
    SessionFilterSerializer,
    ReasoningSessionSerializer,
    ReasoningSessionDetailSerializer,
    ReasoningSessionListSerializer,
    ReasoningSessionChunkSerializer,
    StatsResponseSerializer,
    ChunkResponseSerializer,
)
from .pipeline import ReasoningPipeline, ReasoningResult, ReasoningError

logger = logging.getLogger(__name__)


class QueryView(APIView):
    """
    POST /api/reasoning/query/

    Run the reasoning pipeline on a query.

    Request body:
        - query: The user's query (required)
        - subject_id: Subject ID to search within (required)
        - conversation_history: Previous conversation exchanges (optional)
        - pipeline_name: Retrieval pipeline to use (optional)

    Returns:
        QueryResponseSerializer data with reasoning results.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Execute the reasoning pipeline."""
        # Validate input
        serializer = QueryInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        query = validated_data['query']
        subject_id = validated_data['subject_id']
        conversation_history = validated_data.get('conversation_history', [])
        pipeline_name = validated_data.get('pipeline_name') or None

        logger.info(
            f"Reasoning query from user {request.user.id}: "
            f"'{query[:50]}...' (subject_id={subject_id})"
        )

        try:
            # Run the reasoning pipeline
            pipeline = ReasoningPipeline()
            result: ReasoningResult = pipeline.run(
                query=query,
                subject_id=subject_id,
                conversation_history=conversation_history,
                pipeline_name=pipeline_name,
            )

            # Persist the session
            session = ReasoningSession.create_from_result(result)

            # Build response
            response_data = {
                'session_id': session.session_id,
                'original_query': result.original_query,
                'classification_category': (
                    result.classification_result.category.value
                    if result.classification_result else 'unknown'
                ),
                'rewritten_query': result.rewritten_query,
                'pipeline_name': result.pipeline_name,
                'final_answer': result.final_answer,
                'confidence_score': (
                    result.confidence_score.final_score
                    if result.confidence_score else 0.0
                ),
                'confidence_interpretation': (
                    result.confidence_score.interpretation
                    if result.confidence_score else 'UNKNOWN'
                ),
                'unverified': result.unverified_flag,
                'retry_count': len(result.retry_results),
                'total_latency_ms': result.total_latency_ms,
                'retrieved_chunk_count': len(result.retrieved_chunks),
                'faithfulness_score': (
                    result.verification_result.faithfulness_score
                    if result.verification_result else None
                ),
                'generated_answer': result.generated_answer,
                'latency_breakdown': result.latency_breakdown,
                'verification_reasoning': (
                    result.verification_result.reasoning
                    if result.verification_result else None
                ),
            }

            logger.info(
                f"Reasoning complete for session {session.session_id}: "
                f"confidence={response_data['confidence_score']:.2f}, "
                f"verified={not result.unverified_flag}"
            )

            return Response(response_data, status=status.HTTP_200_OK)

        except ReasoningError as e:
            logger.error(f"Reasoning pipeline error: {str(e)}")
            return Response(
                {'error': 'Reasoning pipeline failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error in reasoning query: {str(e)}")
            return Response(
                {'error': 'Internal server error', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SessionListView(APIView):
    """
    GET /api/reasoning/sessions/

    List reasoning sessions with filters.

    Query parameters:
        - pipeline_name: Filter by pipeline name
        - classification_category: Filter by classification
        - confidence_min/confidence_max: Filter by confidence score range
        - confidence_interpretation: Filter by interpretation
        - unverified: Filter by verification status
        - subject_id: Filter by subject
        - start_date/end_date: Filter by date range
        - limit: Maximum results (default 100, max 1000)
        - offset: Pagination offset

    Returns:
        List of ReasoningSessionListSerializer data.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List sessions with filtering."""
        # Validate filter parameters
        filter_serializer = SessionFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(
                {'error': 'Invalid filter parameters', 'details': filter_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        filters = filter_serializer.validated_data

        # Build queryset
        queryset = ReasoningSession.objects.all()

        # Apply filters
        if filters.get('pipeline_name'):
            queryset = queryset.filter(pipeline_name=filters['pipeline_name'])

        if filters.get('classification_category'):
            queryset = queryset.filter(
                classification_category=filters['classification_category']
            )

        if filters.get('confidence_min') is not None:
            queryset = queryset.filter(confidence_score__gte=filters['confidence_min'])

        if filters.get('confidence_max') is not None:
            queryset = queryset.filter(confidence_score__lte=filters['confidence_max'])

        if filters.get('confidence_interpretation'):
            queryset = queryset.filter(
                confidence_interpretation=filters['confidence_interpretation']
            )

        if filters.get('unverified') is not None:
            queryset = queryset.filter(unverified=filters['unverified'])

        if filters.get('subject_id'):
            queryset = queryset.filter(subject_id=filters['subject_id'])

        if filters.get('start_date'):
            queryset = queryset.filter(created_at__gte=filters['start_date'])

        if filters.get('end_date'):
            queryset = queryset.filter(created_at__lte=filters['end_date'])

        # Apply pagination
        limit = filters.get('limit', 100)
        offset = filters.get('offset', 0)
        total_count = queryset.count()
        queryset = queryset[offset:offset + limit]

        # Serialize
        serializer = ReasoningSessionListSerializer(queryset, many=True)

        return Response({
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'sessions': serializer.data,
        }, status=status.HTTP_200_OK)


class SessionDetailView(APIView):
    """
    GET /api/reasoning/sessions/<id>/

    Get detailed session information.

    Path parameters:
        - session_id: UUID of the session

    Returns:
        ReasoningSessionDetailSerializer data.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        """Get session details."""
        try:
            # Try to parse as UUID
            try:
                session_uuid = UUID(str(session_id))
            except ValueError:
                return Response(
                    {'error': 'Invalid session ID format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            session = ReasoningSession.objects.prefetch_related('chunks').get(
                session_id=session_uuid
            )
            serializer = ReasoningSessionDetailSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ReasoningSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SessionChunksView(APIView):
    """
    GET /api/reasoning/sessions/<id>/chunks/

    Get chunks for a specific session.

    Path parameters:
        - session_id: UUID of the session

    Returns:
        ChunkResponseSerializer data with all chunks.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        """Get session chunks."""
        try:
            # Parse UUID
            try:
                session_uuid = UUID(str(session_id))
            except ValueError:
                return Response(
                    {'error': 'Invalid session ID format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            session = ReasoningSession.objects.get(session_id=session_uuid)
            chunks = session.chunks.all()

            # Separate initial and retry chunks
            initial_chunks = chunks.filter(used_in_retry=False)
            retry_chunks = chunks.filter(used_in_retry=True)

            serializer = ReasoningSessionChunkSerializer(chunks, many=True)

            return Response({
                'session_id': session.session_id,
                'total_chunks': chunks.count(),
                'initial_chunks': initial_chunks.count(),
                'retry_chunks': retry_chunks.count(),
                'chunks': serializer.data,
            }, status=status.HTTP_200_OK)

        except ReasoningSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class StatsView(APIView):
    """
    GET /api/reasoning/stats/

    Get aggregated reasoning statistics.

    Query parameters:
        - pipeline_name: Filter by pipeline (optional)
        - subject_id: Filter by subject (optional)
        - start_date/end_date: Filter by date range (optional)

    Returns:
        StatsResponseSerializer data with aggregate stats.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get aggregate stats."""
        queryset = ReasoningSession.objects.all()

        # Apply optional filters
        pipeline_name = request.query_params.get('pipeline_name')
        subject_id = request.query_params.get('subject_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if pipeline_name:
            queryset = queryset.filter(pipeline_name=pipeline_name)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        # Calculate aggregates
        total_sessions = queryset.count()

        if total_sessions == 0:
            return Response({
                'total_sessions': 0,
                'avg_confidence_score': None,
                'avg_faithfulness_score': None,
                'avg_latency_ms': None,
                'classification_breakdown': {},
                'confidence_breakdown': {},
                'unverified_rate': 0.0,
                'avg_retry_count': None,
                'retry_rate': 0.0,
                'date_range': None,
            }, status=status.HTTP_200_OK)

        # Aggregate calculations
        aggregates = queryset.aggregate(
            avg_confidence=Avg('confidence_score'),
            avg_faithfulness=Avg('faithfulness_score'),
            avg_latency=Avg('total_latency'),
            avg_retries=Avg('retry_count'),
            min_date=Min('created_at'),
            max_date=Max('created_at'),
        )

        # Unverified count
        unverified_count = queryset.filter(unverified=True).count()
        unverified_rate = unverified_count / total_sessions if total_sessions > 0 else 0.0

        # Retry rate (sessions with at least one retry)
        sessions_with_retry = queryset.filter(retry_count__gt=0).count()
        retry_rate = sessions_with_retry / total_sessions if total_sessions > 0 else 0.0

        # Classification breakdown
        classification_counts = queryset.values('classification_category').annotate(
            count=Count('id')
        )
        classification_breakdown = {
            item['classification_category']: item['count']
            for item in classification_counts
        }

        # Confidence interpretation breakdown
        confidence_counts = queryset.values('confidence_interpretation').annotate(
            count=Count('id')
        )
        confidence_breakdown = {
            item['confidence_interpretation']: item['count']
            for item in confidence_counts
            if item['confidence_interpretation']  # Exclude empty strings
        }

        # Build response
        response_data = {
            'total_sessions': total_sessions,
            'avg_confidence_score': aggregates['avg_confidence'],
            'avg_faithfulness_score': aggregates['avg_faithfulness'],
            'avg_latency_ms': aggregates['avg_latency'],
            'classification_breakdown': classification_breakdown,
            'confidence_breakdown': confidence_breakdown,
            'unverified_rate': round(unverified_rate, 4),
            'avg_retry_count': aggregates['avg_retries'],
            'retry_rate': round(retry_rate, 4),
            'date_range': {
                'start': aggregates['min_date'].isoformat() if aggregates['min_date'] else None,
                'end': aggregates['max_date'].isoformat() if aggregates['max_date'] else None,
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)
