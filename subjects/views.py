from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.contrib import messages
from django.conf import settings
from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.throttling import ScopedRateThrottle
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone
import logging

from .models import (
    Subject, SubjectMaterial, Flashcard, FlashcardReview, QuizQuestion, QuizAttempt,
    Quiz, Choice, UserQuizAttempt, UserAnswer,
    ChatSession, ChatMessage, delete_subjects
)
from .serializers import (
    SubjectSerializer, SubjectMaterialSerializer, FlashcardSerializer,
    QuizQuestionSerializer, QuizAnswerSerializer,
    ChatSessionSerializer, ChatMessageSerializer, ChatMessageCreateSerializer,
)
from .permissions import IsSubjectOwner, ChatAPIPermission, IsChatSessionOwner
from .services.rag_service import RAGService
from .services.session_manager import SessionManager
from .tasks import process_material
from .utils import material_file_type, short_answer_matches, upload_problem
from .app_api import due_by_subject, subject_summaries
from .quiz_api import _unfinished_attempts
import json
import os

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # matches the "up to 100 MB" promise in the upload dialog
from django.utils import timezone
from django.db import models

logger = logging.getLogger(__name__)

# Create your views here.

# Web Interface Views
@login_required
def create_subject(request):
    """Handle subject creation from form submission"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            try:
                subject = Subject.objects.create(user=request.user, name=name)
                messages.success(request, f'Subject "{name}" created successfully!')
                return redirect('subjects')
            except Exception as e:
                messages.error(request, f'Failed to create subject: {str(e)}')
        else:
            messages.error(request, 'Subject name is required.')
    
    return redirect('subjects')

@login_required
def upload_material(request, pk):
    """Handle material upload from form submission"""
    subject = get_object_or_404(Subject, id=pk, user=request.user)
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')

        if uploaded_file:
            try:
                file_type = material_file_type(uploaded_file.name)
                if not file_type:
                    messages.error(request, 'Unsupported file type. Please upload PDF, Word (DOC/DOCX), video (MP4/MOV/AVI), or audio (MP3/WAV/M4A) files.')
                    return redirect('subject_detail', pk=pk)

                with transaction.atomic():
                    material = SubjectMaterial.objects.create(
                        subject=subject,
                        file=uploaded_file,
                        file_type=file_type,
                        status='PENDING'
                    )
                    # Only queue the main processing task - it will handle the rest
                    try:
                        process_material.delay(material.id)
                    except Exception as e:
                        logger.error(f"Could not queue processing for material {material.id}: {e}")
                        material.status = 'FAILED'
                        material.save()

                if material.status == 'FAILED':
                    messages.error(request, f'"{uploaded_file.name}" was saved but processing could not start. Please try again later.')
                else:
                    messages.success(request, f'Material "{uploaded_file.name}" uploaded successfully! Quiz generation started.')
                return redirect('subject_detail', pk=pk)

            except Exception as e:
                logger.exception(f"Error creating material for subject {pk}: {e}")
                messages.error(request, f'Failed to upload material: {str(e)}')
        else:
            messages.error(request, 'Please select a file to upload.')

    return redirect('subject_detail', pk=pk)

@login_required
def delete_material(request, pk, material_id):
    """Delete a subject material"""
    subject = get_object_or_404(Subject, id=pk, user=request.user)
    material = get_object_or_404(SubjectMaterial, id=material_id, subject=subject)
    
    if request.method == 'POST':
        # Store filename for success message
        filename = material.display_name or 'Unknown file'
        
        # Delete the stored file through its storage backend (local or S3)
        if material.file:
            material.file.delete(save=False)
        
        # Delete the material (this will cascade delete related objects)
        material.delete()
        
        messages.success(request, f'Material "{filename}" has been deleted successfully.')
    
    return redirect('subject_detail', pk=pk)

@login_required
def material_status(request, material_id):
    """API endpoint to check material processing status"""
    material = get_object_or_404(SubjectMaterial, id=material_id, subject__user=request.user)
    
    return JsonResponse({
        'id': material.id,
        'filename': material.display_name or 'Unknown',
        'status': material.status,
        'created_at': material.created_at.isoformat(),
        'updated_at': material.updated_at.isoformat(),
        'chunks_count': material.chunks.count(),
        'flashcards_count': material.flashcards.count(),  # Material-specific flashcards
        'quiz_count': material.subject.quizzes.count()  # Keep quizzes at subject level for now
    })

@login_required
def take_quiz(request, quiz_id):
    """Old quiz links (recommendations, notifications): quizzes are taken in the app now; ?dynamic=true meant fresh questions."""
    fresh = '?fresh=1' if request.GET.get('dynamic', '').lower() == 'true' else ''
    return redirect(f'/app/quizzes/{quiz_id}/start{fresh}')


# XP Chatbot API Views

class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Subject.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save(user=self.request.user)
        except IntegrityError:  # a second click raced the first past the name check
            name = serializer.validated_data['name']
            raise ValidationError({'name': [f'A subject named {name} already exists.']})

    def perform_destroy(self, instance):
        delete_subjects(Subject.objects.filter(pk=instance.pk))

    @action(detail=True, methods=['post'])
    def upload_material(self, request, pk=None):
        subject = self.get_object()
        serializer = SubjectMaterialSerializer(data=request.data)
        uploaded_file = request.FILES.get('file')
        problem = upload_problem(uploaded_file) if uploaded_file else None
        if problem:
            return Response({'file': [problem]}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded_file and uploaded_file.size > MAX_UPLOAD_BYTES:
            return Response({'file': ['Files can be up to 100 MB.']}, status=status.HTTP_400_BAD_REQUEST)

        if serializer.is_valid():
            material = serializer.save(subject=subject, file_type=material_file_type(uploaded_file.name),
                                       original_name=os.path.basename(uploaded_file.name)[:255])
            # process_material queues flashcard and quiz generation itself
            process_material.delay(material.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Every subject with material count, due cards, latest quiz score and last update (for the app)."""
        return Response(subject_summaries(request.user, due_by_subject(request.user)))

    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        subject = self.get_object()
        materials = SubjectMaterial.objects.filter(subject=subject).prefetch_related('quizzes').order_by('-created_at')
        serializer = SubjectMaterialSerializer(materials, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def quiz_results(self, request, pk=None):
        """Get quiz attempts and results for this subject"""
        subject = self.get_object()
        
        # Get all quiz attempts for this subject
        attempts = UserQuizAttempt.objects.filter(
            quiz__subject=subject,
            user=request.user,
            is_completed=True
        ).select_related('quiz').order_by('-start_time')
        
        # Format the results
        results_data = []
        for attempt in attempts:
            # Handle None values gracefully
            score = attempt.score if attempt.score is not None else 0
            earned_points = attempt.earned_points if attempt.earned_points is not None else 0
            total_points = attempt.total_points if attempt.total_points is not None else 0
            
            results_data.append({
                'id': attempt.id,
                'quiz_title': attempt.quiz.title,
                'score': round(score, 1),
                'earned_points': earned_points,
                'total_points': total_points,
                'passed': attempt.is_passed(),
                'start_time': attempt.start_time.isoformat(),
                'end_time': attempt.end_time.isoformat() if attempt.end_time else None,
                'duration': str(attempt.end_time - attempt.start_time) if attempt.end_time else None,
                'question_count': attempt.user_answers.count(),
                'correct_answers': attempt.user_answers.filter(is_correct=True).count(),
                'uses_dynamic_questions': attempt.uses_dynamic_questions
            })
        
        # Calculate subject statistics
        total_attempts = attempts.count()
        avg_score = attempts.aggregate(avg_score=models.Avg('score'))['avg_score'] or 0
        best_score = attempts.aggregate(max_score=models.Max('score'))['max_score'] or 0
        
        return Response({
            'attempts': results_data,
            'statistics': {
                'total_attempts': total_attempts,
                'average_score': round(avg_score, 1),
                'best_score': round(best_score, 1)
            }
        })

    @action(detail=True, methods=['get'])
    def flashcards(self, request, pk=None):
        subject = self.get_object()
        flashcards = (Flashcard.objects.filter(subject=subject).select_related('material')
                      .prefetch_related(Prefetch('reviews', queryset=FlashcardReview.objects.filter(user=request.user),
                                                 to_attr='my_reviews')))
        serializer = FlashcardSerializer(flashcards, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def quizzes(self, request, pk=None):
        """Get all quizzes for a subject"""
        subject = self.get_object()
        quizzes = Quiz.objects.filter(subject=subject)
        quiz_data = []
        
        for quiz in quizzes.select_related('material'):
            scores = list(quiz.attempts.filter(user=request.user, is_completed=True, score__isnull=False)
                          .order_by('-end_time', '-id').values_list('score', flat=True))
            quiz_data.append({
                'material_id': quiz.material_id,
                'material_name': quiz.material.display_name if quiz.material else None,
                'attempts': len(scores),
                'last_score': round(scores[0]) if scores else None,
                'best_score': round(max(scores)) if scores else None,
                'has_unfinished_attempt': _unfinished_attempts(request.user, quiz).exists(),
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'question_count': quiz.questions.count(),
                'total_points': sum(q.points for q in quiz.questions.all()),
                'time_limit': quiz.time_limit,
                'pass_score': quiz.pass_score,
                'created_at': quiz.created_at
            })
        
        return Response(quiz_data)

    @action(detail=True, methods=['get'])
    def quiz_questions(self, request, pk=None):
        """Legacy endpoint - keep for backward compatibility"""
        subject = self.get_object()
        questions = QuizQuestion.objects.filter(subject=subject)
        serializer = QuizQuestionSerializer(questions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def submit_quiz(self, request, pk=None):
        """Legacy endpoint - keep for backward compatibility"""
        subject = self.get_object()
        serializer = QuizAnswerSerializer(data=request.data, many=True)
        
        if serializer.is_valid():
            answers = serializer.validated_data
            results = []
            
            for answer in answers:
                question = get_object_or_404(QuizQuestion, id=answer['question_id'], subject=subject)
                is_correct = answer['selected_answer'] == question.correct_answer
                
                attempt = QuizAttempt.objects.create(
                    user=request.user,
                    quiz_question=question,
                    selected_answer=answer['selected_answer'],
                    used_hint=answer['used_hint'],
                    is_correct=is_correct
                )
                
                results.append({
                    'question_id': question.id,
                    'is_correct': is_correct
                })
            
            return Response(results)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubjectMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectMaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Uploads go through SubjectViewSet.upload_material so they get a subject and processing
    http_method_names = ['get', 'delete', 'head', 'options']

    def get_queryset(self):
        return SubjectMaterial.objects.filter(subject__user=self.request.user)

    def perform_destroy(self, instance):
        if instance.file:
            instance.file.delete(save=False)  # the stored file too (local or S3), like the old delete page
        instance.delete()

    @action(detail=True, methods=['get'])
    def flashcards(self, request, pk=None):
        material = self.get_object()
        flashcards = Flashcard.objects.filter(material=material)  # Filter by specific material
        serializer = FlashcardSerializer(flashcards, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def quiz(self, request, pk=None):
        """Get quiz for this specific material"""
        material = self.get_object()
        try:
            # Use the material field to find the quiz
            quiz = Quiz.objects.get(material=material)
            
            questions_data = []
            for question in quiz.questions.all().order_by('order'):
                question_data = {
                    'id': question.id,
                    'text': question.text,
                    'type': question.question_type,
                    'points': question.points,
                    'explanation': question.explanation
                }
                
                if question.question_type in ['multiple_choice', 'true_false']:
                    question_data['choices'] = [
                        {
                            'id': choice.id,
                            'text': choice.text,
                            'order': choice.order
                        }
                        for choice in question.choices.all().order_by('order')
                    ]
                
                questions_data.append(question_data)
            
            return Response({
                'quiz': {
                    'id': quiz.id,
                    'title': quiz.title,
                    'description': quiz.description,
                    'time_limit': quiz.time_limit,
                    'pass_score': quiz.pass_score,
                    'total_points': sum(q.points for q in quiz.questions.all())
                },
                'questions': questions_data
            })
            
        except Quiz.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

class QuizViewSet(viewsets.ModelViewSet):
    """API endpoints for the new quiz system"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Quiz.objects.filter(subject__user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get all questions for a quiz"""
        quiz = self.get_object()
        questions_data = []
        
        for question in quiz.questions.all().order_by('order'):
            question_data = {
                'id': question.id,
                'text': question.text,
                'type': question.question_type,
                'points': question.points,
                'explanation': question.explanation
            }
            
            if question.question_type in ['multiple_choice', 'true_false']:
                question_data['choices'] = [
                    {
                        'id': choice.id,
                        'text': choice.text,
                        'order': choice.order
                    }
                    for choice in question.choices.all().order_by('order')
                ]
            
            questions_data.append(question_data)
        
        return Response(questions_data)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit quiz answers and get results"""
        quiz = self.get_object()
        answers = request.data.get('answers', {})
        
        # Create quiz attempt
        quiz_attempt = UserQuizAttempt.objects.create(
            user=request.user,
            quiz=quiz
        )
        
        total_points = 0
        earned_points = 0
        results = []
        
        # Process each answer
        for question in quiz.questions.all():
            user_answer = answers.get(str(question.id))
            if not user_answer:
                continue
            
            total_points += question.points
            is_correct = False
            
            # Check answer based on question type
            if question.question_type in ['multiple_choice', 'true_false']:
                try:
                    selected_choice = question.choices.get(id=int(user_answer))
                    is_correct = selected_choice.is_correct
                    answer_text = selected_choice.text
                except (ValueError, Choice.DoesNotExist):
                    answer_text = str(user_answer)
            
            elif question.question_type == 'short_answer':
                answer_text = str(user_answer)
                # Check against all possible correct answers
                correct_answers = question.answers.filter(is_correct=True).values_list('text', flat=True)
                is_correct = short_answer_matches(answer_text, correct_answers)
            
            # Award points if correct
            if is_correct:
                earned_points += question.points
            
            # Save user answer
            UserAnswer.objects.create(
                attempt=quiz_attempt,
                question=question,
                answer_text=answer_text,
                is_correct=is_correct
            )
            
            results.append({
                'question_id': question.id,
                'is_correct': is_correct,
                'explanation': question.explanation
            })
        
        # Calculate final score and complete attempt
        quiz_attempt.total_points = total_points
        quiz_attempt.earned_points = earned_points
        quiz_attempt.complete_attempt()  # This sets end_time and calculates score
        
        return Response({
            'attempt_id': quiz_attempt.id,
            'score_percentage': quiz_attempt.calculate_score(),
            'passed': quiz_attempt.is_passed(),
            'total_points': total_points,
            'earned_points': earned_points,
            'results': results
        })


# XP Chatbot API Views

class ChatSessionCreateAPIView(generics.CreateAPIView):
    """
    API endpoint for creating new chat sessions.
    
    POST /api/subjects/{subject_id}/chat/session/
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsSubjectOwner]
    
    def perform_create(self, serializer):
        """Create a new chat session for the specified subject."""
        subject_id = self.kwargs.get('subject_id')
        subject = get_object_or_404(Subject, id=subject_id, user=self.request.user)
        
        # Deactivate any existing sessions for this user-subject pair
        ChatSession.objects.filter(
            user=self.request.user,
            subject=subject,
            is_active=True
        ).update(is_active=False)
        
        # Create new active session
        serializer.save(user=self.request.user, subject=subject, is_active=True)
        
        logger.info(f"Created new chat session for user {self.request.user.id} and subject {subject_id}")


class ChatSessionListAPIView(generics.ListAPIView):
    """
    API endpoint for listing chat sessions for a subject with history filtering.
    
    GET /api/subjects/{subject_id}/chat/sessions/
    Query params:
    - limit: Number of sessions to return (default: 30, max: 100)
    - status: Filter by session status ('active', 'expired', 'archived')
    - include_inactive: Include inactive sessions (default: true)
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsSubjectOwner]
    
    def get_queryset(self):
        """Get chat sessions for the subject owned by the current user with filtering."""
        subject_id = self.kwargs.get('subject_id')
        subject = get_object_or_404(Subject, id=subject_id, user=self.request.user)
        
        # Get query parameters
        limit = min(int(self.request.query_params.get('limit', 30)), 100)
        status_filter = self.request.query_params.get('status')
        include_inactive = self.request.query_params.get('include_inactive', 'true').lower() == 'true'
        
        queryset = ChatSession.objects.filter(
            subject=subject,
            user=self.request.user
        )
        
        # Apply status filter
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Apply inactive filter
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        # Order by last activity (most recent first) and limit results
        return queryset.select_related('subject', 'user').prefetch_related('messages').order_by('-last_activity', '-updated_at')[:limit]

    def list(self, request, *args, **kwargs):
        """Enhanced list response with metadata for chat history"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Add metadata about session history
        subject_id = kwargs.get('subject_id')
        total_sessions = ChatSession.objects.filter(
            subject_id=subject_id,
            user=request.user
        ).count()
        
        active_sessions = ChatSession.objects.filter(
            subject_id=subject_id,
            user=request.user,
            status='active',
            is_active=True
        ).count()
        
        return Response({
            'sessions': serializer.data,
            'metadata': {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'returned_count': len(serializer.data),
                'max_limit': 100
            }
        })


class ChatMessageListCreateAPIView(generics.ListCreateAPIView):
    """
    API endpoint for chat messages.
    
    GET /api/subjects/{subject_id}/chat/messages/ - Get chat history
    POST /api/subjects/{subject_id}/chat/messages/ - Send a message and get XP response
    """
    permission_classes = [permissions.IsAuthenticated, ChatAPIPermission]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'POST':
            return ChatMessageCreateSerializer
        return ChatMessageSerializer
    
    def get_queryset(self):
        """Get chat messages for the active session of this subject."""
        subject_id = self.kwargs.get('subject_id')
        subject = get_object_or_404(Subject, id=subject_id, user=self.request.user)
        
        # Get the active session for this user-subject pair
        try:
            session = ChatSession.objects.get(
                user=self.request.user,
                subject=subject,
                is_active=True
            )
            return ChatMessage.objects.filter(session=session).order_by('timestamp')
        except ChatSession.DoesNotExist:
            # Return empty queryset if no active session
            return ChatMessage.objects.none()
    
    def list(self, request, *args, **kwargs):
        """
        Return chat history with pagination and session info.
        """
        subject_id = self.kwargs.get('subject_id')
        subject = get_object_or_404(Subject, id=subject_id, user=self.request.user)

        session_id = request.query_params.get('session_id')
        if session_id:
            # A specific past conversation (the app's history list); only the user's own, on this subject
            if not session_id.isdigit():
                return Response({'session_id': ['Must be a number.']}, status=status.HTTP_400_BAD_REQUEST)
            session = get_object_or_404(ChatSession, id=int(session_id), user=request.user, subject=subject)
            messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
            return Response({
                'session': ChatSessionSerializer(session).data,
                'messages': ChatMessageSerializer(messages, many=True).data,
                'total_messages': messages.count(),
                'has_more': False,
            })

        try:
            session = ChatSession.objects.get(
                user=self.request.user,
                subject=subject,
                is_active=True
            )
            
            messages = self.get_queryset()
            page = self.paginate_queryset(messages)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response = self.get_paginated_response(serializer.data)
                # Add session info to response
                response.data['session'] = ChatSessionSerializer(session).data
                return response
            
            serializer = self.get_serializer(messages, many=True)
            return Response({
                'session': ChatSessionSerializer(session).data,
                'messages': serializer.data,
                'total_messages': len(serializer.data),
                'has_more': False
            })
            
        except ChatSession.DoesNotExist:
            return Response({
                'session': None,
                'messages': [],
                'total_messages': 0,
                'has_more': False
            })
    
    throttle_scope = 'llm'

    def get_throttles(self):
        # Only sending costs LLM calls; reading history stays unlimited
        return [ScopedRateThrottle()] if self.request.method == 'POST' else []

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Send a message and get XP response using RAG pipeline.
        """
        subject_id = self.kwargs.get('subject_id')
        subject = get_object_or_404(Subject, id=subject_id, user=self.request.user)
        
        # Validate input
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_message_content = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')
        
        try:
            session_manager, session, user_message, chat_history = self._start_exchange(subject, user_message_content, session_id)

            logger.info(f"Generating RAG response for user {request.user.id}, subject {subject_id}, query: {user_message_content[:100]}...")
            rag_response = RAGService().generate_response(
                query=user_message_content,
                subject_id=subject.id,
                chat_history=chat_history,
                user_id=request.user.id
            )
            assistant_message = self._finish_exchange(session_manager, session, subject, user_message_content, rag_response)

            logger.info(f"Successfully generated chat response for user {request.user.id}, session {session.id}")

            return Response(
                self._exchange_payload(user_message, assistant_message, session, rag_response),
                status=status.HTTP_201_CREATED,
            )

        except Http404:
            raise  # e.g. a session_id that isn't theirs: a 404, not "XP is unavailable"
        except Exception as e:
            logger.error(f"Error generating chat response for user {request.user.id}, subject {subject_id}: {str(e)}")
            
            # Return error response
            return Response({
                'error': 'Failed to generate response',
                'message': 'XP is currently unavailable. Please try again later.',
                'details': str(e) if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _start_exchange(self, subject, user_message_content, session_id=None):
        """Get/extend the session (or resume `session_id`), save the user's message, and build the chat history for RAG."""
        session_manager = SessionManager()
        if session_id:
            session, created = session_manager.resume_session(self.request.user, subject, session_id), False
        else:
            session, created = session_manager.get_or_create_session(
                user=self.request.user,
                subject=subject,
                content=user_message_content  # Used for title generation
            )
        if created:
            logger.info(f"Created new chat session {session.id} for user {self.request.user.id} and subject {subject.id}")

        user_message = ChatMessage.objects.create(session=session, role='user', content=user_message_content, metadata={})

        # Last 20 messages (10 exchanges), paired as user/assistant in chronological order
        previous = list(reversed(
            ChatMessage.objects.filter(session=session).exclude(id=user_message.id).order_by('-timestamp')[:20]
        ))
        chat_history = [
            {'user': previous[i].content, 'assistant': previous[i + 1].content}
            for i in range(0, len(previous) - 1, 2)
            if previous[i].role == 'user' and previous[i + 1].role == 'assistant'
        ]
        return session_manager, session, user_message, chat_history

    def _finish_exchange(self, session_manager, session, subject, user_message_content, rag_response):
        """Save the assistant's reply, extend the session, and title new conversations."""
        assistant_message = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=rag_response['response'],
            metadata={
                'retrieved_chunks': rag_response['retrieved_chunks'],
                'response_time': rag_response['response_time'],
                'context_used': rag_response['context_used'],
                'model_info': rag_response['metadata']
            }
        )
        session_manager.extend_session(session)
        if not session.title or session.title == "New conversation":
            try:
                session.title = self._generate_session_title(user_message_content, rag_response['response'], subject.name)
                session.save(update_fields=['title'])
            except Exception as e:
                logger.warning(f"Failed to generate title for session {session.id}: {str(e)}")
        return assistant_message

    def _exchange_payload(self, user_message, assistant_message, session, rag_response):
        return {
            'user_message': ChatMessageSerializer(user_message).data,
            'assistant_message': ChatMessageSerializer(assistant_message).data,
            'session': ChatSessionSerializer(session).data,
            'response_metadata': {
                'chunks_retrieved': len(rag_response['retrieved_chunks']),
                'response_time_seconds': rag_response['response_time'],
                'context_was_used': rag_response['context_used']
            }
        }

    def _generate_session_title(self, user_message, assistant_response, subject_name):
        """Generate a concise title for the chat session based on the first exchange."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # The subject name is left out: a Spanish subject name pulled English questions' titles into Spanish
            prompt = f"""Based on this conversation, create a concise, descriptive title (max 50 characters) that captures the main topic:

User: {user_message[:200]}
Assistant: {assistant_response[:200]}

Generate a title that is:
- Specific to the topic discussed
- Maximum 50 characters
- Clear and descriptive
- No quotes or special formatting
- Written in the same language as the User line above

Title:"""
            
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=50,
                temperature=0.7
            )
            
            title = response.choices[0].message.content.strip()
            
            # Clean up the title and ensure it's not too long
            title = title.replace('"', '').replace("'", '').strip()
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title if title else "New conversation"
            
        except Exception as e:
            logger.warning(f"Failed to generate session title: {str(e)}")
            return "New conversation"


class EventStreamRenderer(BaseRenderer):
    """Lets DRF accept `Accept: text/event-stream` (it answers 406 otherwise). The stream itself is a
    StreamingHttpResponse; this only renders non-stream replies such as validation errors, as JSON."""
    media_type = 'text/event-stream'
    format = 'sse'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return json.dumps(data).encode()


class ChatMessageStreamAPIView(ChatMessageListCreateAPIView):
    """
    POST /api/subjects/{subject_id}/chat/stream/

    Same as sending a message, but the answer arrives as Server-Sent Events while it is written:
    `token` ({"text"}) events, then one `done` event with the same payload as the normal endpoint
    (its assistant_message is authoritative: a verification retry may replace the streamed text),
    or one `error` event.
    """
    http_method_names = ['post', 'options']
    renderer_classes = [JSONRenderer, EventStreamRenderer]

    def create(self, request, *args, **kwargs):
        subject = get_object_or_404(Subject, id=self.kwargs.get('subject_id'), user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data['message']
        session_manager, session, user_message, chat_history = self._start_exchange(
            subject, content, serializer.validated_data.get('session_id'))

        def sse(event, data):
            return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

        def events():
            try:
                rag_response = None
                for kind, value in RAGService().respond_events(
                        content, subject.id, chat_history, request.user.id, stream=True):
                    if kind == 'token':
                        yield sse('token', {'text': value})
                    else:
                        rag_response = value
                assistant_message = self._finish_exchange(session_manager, session, subject, content, rag_response)
                yield sse('done', self._exchange_payload(user_message, assistant_message, session, rag_response))
            except Exception as e:
                logger.error(f"Error streaming chat response for user {request.user.id}, subject {subject.id}: {e}")
                yield sse('error', {'message': 'XP is currently unavailable. Please try again later.'})

        response = StreamingHttpResponse(events(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # stop nginx buffering the stream
        return response


class ChatSessionValidateAPIView(APIView):
    """
    API endpoint for validating chat sessions and checking if they're still active.
    
    GET /api/subjects/{subject_id}/chat/sessions/{session_id}/validate/
    """
    permission_classes = [permissions.IsAuthenticated, IsSubjectOwner]
    
    def get(self, request, subject_id, session_id):
        """Validate that a session exists, belongs to the user, and is still active."""
        subject = get_object_or_404(Subject, id=subject_id, user=request.user)
        
        try:
            session_manager = SessionManager()
            session = session_manager.validate_session(session_id, request.user, subject)
            
            if session:
                # Session is valid and active
                return Response({
                    'valid': True,
                    'session': ChatSessionSerializer(session).data,
                    'message': 'Session is active and valid'
                })
            else:
                # Session is invalid or expired
                return Response({
                    'valid': False,
                    'session': None,
                    'message': 'Session is expired or invalid'
                }, status=status.HTTP_410_GONE)
                
        except Exception as e:
            logger.error(f"Error validating session {session_id} for user {request.user.id}: {str(e)}")
            return Response({
                'valid': False,
                'session': None,
                'message': 'Error validating session'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatSessionDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for individual chat session operations.
    
    GET /api/chat/sessions/{session_id}/ - Get session details
    PATCH /api/chat/sessions/{session_id}/ - Update session (e.g., title)
    DELETE /api/chat/sessions/{session_id}/ - Delete session
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsChatSessionOwner]
    
    def get_queryset(self):
        """Get sessions owned by the current user."""
        return ChatSession.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Delete the chat session and all its messages."""
        session = self.get_object()
        session_id = session.id
        user_id = request.user.id
        
        # Delete the session (messages will be cascade deleted)
        self.perform_destroy(session)
        
        logger.info(f"Deleted chat session {session_id} for user {user_id}")
        
        return Response({
            'message': 'Chat session deleted successfully',
            'session_id': session_id
        }, status=status.HTTP_200_OK)


class ChatStatsAPIView(APIView):
    """
    API endpoint for chat statistics and status.
    
    GET /api/subjects/{subject_id}/chat/stats/
    """
    permission_classes = [permissions.IsAuthenticated, IsSubjectOwner]
    
    def get(self, request, subject_id):
        """Get chat statistics and readiness status for a subject."""
        subject = get_object_or_404(Subject, id=subject_id, user=request.user)
        
        try:
            # Get RAG service stats
            rag_service = RAGService()
            rag_stats = rag_service.get_service_stats(subject.id)
            
            # Get chat session stats
            session_count = ChatSession.objects.filter(
                user=request.user,
                subject=subject
            ).count()
            
            active_session = ChatSession.objects.filter(
                user=request.user,
                subject=subject,
                is_active=True
            ).first()
            
            total_messages = ChatMessage.objects.filter(
                session__user=request.user,
                session__subject=subject
            ).count()
            
            # Get recent activity
            recent_messages = ChatMessage.objects.filter(
                session__user=request.user,
                session__subject=subject
            ).order_by('-timestamp')[:5]
            
            return Response({
                'subject_id': subject.id,
                'subject_name': subject.name,
                'chat_ready': rag_stats.get('ready_for_chat', False),
                'total_sessions': session_count,
                'total_messages': total_messages,
                'total_content_chunks': rag_stats.get('total_chunks', 0),
                'is_ready_for_chat': rag_stats.get('ready_for_chat', False),
                'has_active_session': active_session is not None,
                'active_session_id': active_session.id if active_session else None,
                'session_stats': {
                    'total_sessions': session_count,
                    'has_active_session': active_session is not None,
                    'active_session_id': active_session.id if active_session else None,
                    'total_messages': total_messages
                },
                'rag_stats': rag_stats,
                'recent_activity': ChatMessageSerializer(recent_messages, many=True).data,
                'last_activity': recent_messages[0].timestamp if recent_messages else None
            })
            
        except Exception as e:
            logger.error(f"Error getting chat stats for subject {subject_id}: {str(e)}")
            return Response({
                'error': 'Failed to get chat statistics',
                'details': str(e) if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
