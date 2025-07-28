from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
import logging

from .models import (
    Subject, SubjectMaterial, Flashcard, QuizQuestion, QuizAttempt,
    Quiz, Question, Choice, Answer, UserQuizAttempt, UserAnswer,
    ChatSession, ChatMessage
)
from .serializers import (
    SubjectSerializer, SubjectMaterialSerializer, FlashcardSerializer,
    QuizQuestionSerializer, QuizAttemptSerializer, QuizAnswerSerializer,
    ChatSessionSerializer, ChatMessageSerializer, ChatMessageCreateSerializer,
    ChatHistorySerializer, ChatResponseSerializer
)
from .permissions import IsSubjectOwner, ChatAPIPermission, IsChatSessionOwner
from .services.rag_service import RAGService
from .services.session_manager import SessionManager
from .tasks import process_material, generate_quiz_from_material, generate_dynamic_quiz_questions
import json
import os
from django.utils import timezone
from django.db import models
from django.db.models import Avg, Max

logger = logging.getLogger(__name__)

# Create your views here.

# Web Interface Views
class SubjectListView(LoginRequiredMixin, ListView):
    model = Subject
    template_name = 'subjects/subject_list.html'
    context_object_name = 'subjects'

    def get_queryset(self):
        return Subject.objects.filter(user=self.request.user)

class SubjectDetailView(LoginRequiredMixin, DetailView):
    model = Subject
    template_name = 'subjects/subject_detail.html'
    context_object_name = 'subject'

    def get_queryset(self):
        return Subject.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['materials'] = self.object.materials.all()
        # Include quizzes for this subject
        context['quizzes'] = Quiz.objects.filter(subject=self.object)
        return context

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
    
    print(f"Upload material called for subject {pk}")
    print(f"Request method: {request.method}")
    print(f"Request FILES: {request.FILES}")
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        print(f"Uploaded file: {uploaded_file}")
        
        if uploaded_file:
            try:
                print(f"Processing file: {uploaded_file.name}")
                
                # Determine file type
                file_extension = uploaded_file.name.split('.')[-1].upper()
                if file_extension == 'PDF':
                    file_type = 'PDF'
                elif file_extension in ['DOCX']:
                    file_type = 'DOCX'
                elif file_extension in ['DOC']:
                    file_type = 'DOC'
                elif file_extension in ['MP4', 'MOV', 'AVI']:
                    file_type = 'VIDEO'
                else:
                    messages.error(request, 'Unsupported file type. Please upload PDF, Word (DOC/DOCX), or video files.')
                    return redirect('subject_detail', pk=pk)
                
                print(f"File type determined: {file_type}")
                
                # Create the material
                material = SubjectMaterial.objects.create(
                    subject=subject,
                    file=uploaded_file,
                    file_type=file_type,
                    status='PENDING'
                )
                
                print(f"Material created with ID: {material.id}")
                
                # Trigger background processing for material and quiz generation
                try:
                    process_material.delay(material.id)
                    # Also generate quiz from the uploaded material
                    generate_quiz_from_material.delay(material.id, num_questions=10)
                    print("Background tasks queued successfully")
                except Exception as e:
                    # If Celery is not running, just log the error
                    print(f"Background processing failed: {e}")
                
                messages.success(request, f'Material "{uploaded_file.name}" uploaded successfully! Quiz generation started.')
                return redirect('subject_detail', pk=pk)
                
            except Exception as e:
                print(f"Error creating material: {e}")
                messages.error(request, f'Failed to upload material: {str(e)}')
        else:
            print("No file uploaded")
            messages.error(request, 'Please select a file to upload.')
    else:
        print("Not a POST request")
    
    return redirect('subject_detail', pk=pk)

@login_required
def delete_material(request, pk, material_id):
    """Delete a subject material"""
    subject = get_object_or_404(Subject, id=pk, user=request.user)
    material = get_object_or_404(SubjectMaterial, id=material_id, subject=subject)
    
    if request.method == 'POST':
        # Store filename for success message
        filename = os.path.basename(material.file.name) if material.file else 'Unknown file'
        
        # Delete associated file from filesystem
        if material.file and os.path.exists(material.file.path):
            try:
                os.remove(material.file.path)
            except OSError:
                pass  # File might already be deleted
        
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
        'filename': os.path.basename(material.file.name) if material.file else 'Unknown',
        'status': material.status,
        'created_at': material.created_at.isoformat(),
        'updated_at': material.updated_at.isoformat(),
        'chunks_count': material.chunks.count(),
        'flashcards_count': material.flashcards.count(),  # Material-specific flashcards
        'quiz_count': material.subject.quizzes.count()  # Keep quizzes at subject level for now
    })

@login_required
def take_quiz(request, quiz_id):
    """Display quiz taking interface with dynamic questions"""
    quiz = get_object_or_404(Quiz, id=quiz_id, subject__user=request.user)
    
    # Check if user wants dynamic questions (default to false for stability)
    use_dynamic = request.GET.get('dynamic', 'false').lower() == 'true'
    
    if use_dynamic:
        # Check if this is a refresh and we have an existing attempt with questions ready
        attempt_id = request.GET.get('attempt_id')
        if attempt_id:
            try:
                existing_attempt = UserQuizAttempt.objects.get(
                    id=attempt_id, 
                    user=request.user, 
                    quiz=quiz,
                    uses_dynamic_questions=True
                )
                if existing_attempt.dynamic_questions:
                    # Questions are ready, show them
                    context = {
                        'quiz': quiz,
                        'attempt': existing_attempt,
                        'questions': existing_attempt.dynamic_questions,
                        'loading_dynamic': False,
                        'total_questions': len(existing_attempt.dynamic_questions),
                        'total_points': sum(q.get('points', 1) for q in existing_attempt.dynamic_questions),
                        'is_dynamic': True
                    }
                    return render(request, 'subjects/take_quiz.html', context)
            except UserQuizAttempt.DoesNotExist:
                pass
        
        # Always create a fresh attempt for dynamic quizzes
        # This ensures new questions are generated each time
        
        # First, mark any previous uncompleted attempts as abandoned
        UserQuizAttempt.objects.filter(
            user=request.user,
            quiz=quiz,
            uses_dynamic_questions=True,
            end_time__isnull=True  # Not completed yet
        ).update(is_completed=True, end_time=timezone.now())
        
        # Create a new attempt and generate fresh dynamic questions
        attempt = UserQuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            uses_dynamic_questions=True
        )
        
        # Try synchronous generation first for immediate results
        try:
            from .tasks import generate_dynamic_quiz_questions
            
            # Call the task synchronously (without Celery)
            print(f"Attempting synchronous generation for attempt {attempt.id}")
            result = generate_dynamic_quiz_questions(attempt.id, num_questions=10)
            print(f"Synchronous generation result: {result}")
            
            if result.get('status') == 'success' and result.get('questions_generated', 0) > 0:
                # Questions generated successfully, refresh to show them
                attempt.refresh_from_db()
                if attempt.dynamic_questions:
                    print(f"Questions generated successfully: {len(attempt.dynamic_questions)}")
                    context = {
                        'quiz': quiz,
                        'attempt': attempt,
                        'questions': attempt.dynamic_questions,
                        'loading_dynamic': False,
                        'total_questions': len(attempt.dynamic_questions),
                        'total_points': sum(q.get('points', 1) for q in attempt.dynamic_questions),
                        'is_dynamic': True
                    }
                    return render(request, 'subjects/take_quiz.html', context)
                        
        except Exception as e:
            print(f"Synchronous generation failed: {e}")
            import traceback
            traceback.print_exc()
            
            # If API fails, provide user-friendly error and fallback to static questions
            messages.warning(request, "Dynamic question generation is temporarily unavailable. Using static questions instead.")
            
            # Fall back to static questions
            questions = quiz.questions.all().order_by('order')
            if questions.exists():
                context = {
                    'quiz': quiz,
                    'attempt': attempt,
                    'questions': questions,
                    'total_questions': questions.count(),
                    'total_points': sum(q.points for q in questions),
                    'loading_dynamic': False,
                    'is_dynamic': False,
                    'api_error': True
                }
                return render(request, 'subjects/take_quiz.html', context)
            else:
                messages.error(request, "No questions available for this quiz. Please contact support.")
                return redirect('subject_detail', pk=quiz.subject.id)
        
        # Fall back to background generation if sync fails
        try:
            generate_dynamic_quiz_questions.delay(attempt.id, num_questions=10)
        except Exception as e:
            print(f"Background task failed: {e}")
        
        # Show loading message with refresh option
        context = {
            'quiz': quiz,
            'attempt': attempt,
            'loading_dynamic': True,
            'refresh_url': request.build_absolute_uri() + f'?attempt_id={attempt.id}',
            'questions': [],
            'total_questions': 0,
            'total_points': 0,
            'is_dynamic': True
        }
    else:
        # Use static questions (default and reliable)
        questions = quiz.questions.all().order_by('order')
        attempt = UserQuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            uses_dynamic_questions=False
        )
        
        context = {
            'quiz': quiz,
            'attempt': attempt,
            'questions': questions,
            'total_questions': questions.count(),
            'total_points': sum(q.points for q in questions),
            'loading_dynamic': False,
        }
    
    return render(request, 'subjects/take_quiz.html', context)

@login_required
def submit_quiz(request, quiz_id):
    """Handle quiz submission and scoring"""
    if request.method != 'POST':
        return redirect('take_quiz', quiz_id=quiz_id)
    
    quiz = get_object_or_404(Quiz, id=quiz_id, subject__user=request.user)
    
    # Get the attempt ID from the form
    attempt_id = request.POST.get('attempt_id')
    
    if attempt_id:
        # Use existing attempt (for dynamic questions)
        quiz_attempt = get_object_or_404(UserQuizAttempt, id=attempt_id, user=request.user, quiz=quiz)
    else:
        # Create new attempt (for static questions - backwards compatibility)
        quiz_attempt = UserQuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            uses_dynamic_questions=False
        )
    
    total_points = 0
    earned_points = 0
    
    if quiz_attempt.uses_dynamic_questions and quiz_attempt.dynamic_questions:
        # Process dynamic questions
        questions = quiz_attempt.dynamic_questions
        
        for i, question_data in enumerate(questions):
            answer_key = f'question_{question_data["id"]}'
            user_answer_text = request.POST.get(answer_key, '').strip()
            
            if not user_answer_text:
                continue
            
            question_points = question_data.get('points', 1)
            total_points += question_points
            is_correct = False
            
            # Check answer based on question type
            if question_data['type'] == 'multiple_choice':
                try:
                    selected_choice_id = user_answer_text
                    for choice in question_data.get('choices', []):
                        if choice['id'] == selected_choice_id:
                            is_correct = choice['is_correct']
                            user_answer_text = choice['text']
                            break
                except:
                    is_correct = False
            
            elif question_data['type'] == 'true_false':
                try:
                    selected_choice_id = user_answer_text
                    for choice in question_data.get('choices', []):
                        if choice['id'] == selected_choice_id:
                            is_correct = choice['is_correct']
                            user_answer_text = choice['text']
                            break
                except:
                    is_correct = False
            
            elif question_data['type'] == 'short_answer':
                # Check against correct answers
                correct_answers = question_data.get('correct_answers', [])
                for correct_answer in correct_answers:
                    if user_answer_text.lower().strip() in correct_answer.lower().strip():
                        is_correct = True
                        break
            
            # Award points if correct
            if is_correct:
                earned_points += question_points
            
            # Save user answer (we'll need to create a temporary question reference)
            # For dynamic questions, we'll store the question info in the answer_text
            UserAnswer.objects.create(
                attempt=quiz_attempt,
                question=None,  # No actual Question model object for dynamic questions
                answer_text=f"Q: {question_data['text']}\nA: {user_answer_text}",
                is_correct=is_correct
            )
    
    else:
        # Process static questions (existing logic)
        for question in quiz.questions.all():
            answer_key = f'question_{question.id}'
            user_answer_text = request.POST.get(answer_key, '').strip()
            
            if not user_answer_text:
                continue
            
            total_points += question.points
            is_correct = False
            
            # Check answer based on question type
            if question.question_type == 'multiple_choice':
                try:
                    selected_choice_id = int(user_answer_text)
                    selected_choice = question.choices.get(id=selected_choice_id)
                    is_correct = selected_choice.is_correct
                    user_answer_text = selected_choice.text
                except (ValueError, Choice.DoesNotExist):
                    is_correct = False
            
            elif question.question_type == 'true_false':
                try:
                    selected_choice_id = int(user_answer_text)
                    selected_choice = question.choices.get(id=selected_choice_id)
                    is_correct = selected_choice.is_correct
                    user_answer_text = selected_choice.text
                except (ValueError, Choice.DoesNotExist):
                    is_correct = False
            
            elif question.question_type == 'short_answer':
                # Check against all possible correct answers
                correct_answers = question.answers.filter(is_correct=True)
                for answer in correct_answers:
                    if user_answer_text.lower().strip() in answer.text.lower().strip():
                        is_correct = True
                        break
            
            # Award points if correct
            if is_correct:
                earned_points += question.points
            
            # Save user answer
            UserAnswer.objects.create(
                attempt=quiz_attempt,
                question=question,
                answer_text=user_answer_text,
                is_correct=is_correct
            )
    
    # Calculate final score and complete attempt
    quiz_attempt.total_points = total_points
    quiz_attempt.earned_points = earned_points
    quiz_attempt.complete_attempt()  # This sets end_time and calculates score
    
    # Redirect to results page
    return redirect('quiz_results', attempt_id=quiz_attempt.id)

@login_required
def quiz_results(request, attempt_id):
    """Display quiz results"""
    attempt = get_object_or_404(UserQuizAttempt, id=attempt_id, user=request.user)
    user_answers = attempt.user_answers.all().select_related('question')
    
    context = {
        'attempt': attempt,
        'user_answers': user_answers,
        'percentage_score': attempt.calculate_score(),
        'passed': attempt.is_passed(),
        'quiz': attempt.quiz
    }
    
    return render(request, 'subjects/quiz_results.html', context)

@login_required
def check_dynamic_questions(request, attempt_id):
    """Check if dynamic questions are ready for an attempt"""
    attempt = get_object_or_404(UserQuizAttempt, id=attempt_id, user=request.user)
    
    if attempt.dynamic_questions:
        return JsonResponse({
            'ready': True,
            'questions': attempt.dynamic_questions,
            'total_questions': len(attempt.dynamic_questions),
            'total_points': sum(q.get('points', 1) for q in attempt.dynamic_questions)
        })
    else:
        return JsonResponse({'ready': False})

@login_required
def quiz_history(request):
    """Display user's quiz history across all subjects"""
    attempts = UserQuizAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('quiz', 'quiz__subject').order_by('-end_time')[:50]  # Last 50 attempts
    
    context = {
        'attempts': attempts,
    }
    
    return render(request, 'subjects/quiz_history.html', context)

@login_required
def quiz_attempt_detail(request, attempt_id):
    """Display detailed view of a specific quiz attempt"""
    attempt = get_object_or_404(
        UserQuizAttempt,
        id=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    # Get all user answers for this attempt
    user_answers = attempt.user_answers.all().select_related('question')
    
    # Get questions for this attempt (dynamic or static)
    questions = attempt.get_questions()
    
    # Combine questions with user answers for display
    question_results = []
    for question_data in questions:
        # Find the corresponding user answer
        user_answer = None
        if attempt.uses_dynamic_questions:
            # For dynamic questions, find by question text match
            user_answer = user_answers.filter(
                answer_text__icontains=question_data['text'][:30]
            ).first()
        else:
            # For static questions, find by question ID
            user_answer = user_answers.filter(question_id=question_data['id']).first()
        
        question_results.append({
            'question': question_data,
            'user_answer': user_answer,
            'is_correct': user_answer.is_correct if user_answer else False
        })
    
    context = {
        'attempt': attempt,
        'question_results': question_results,
        'total_questions': len(questions),
        'correct_answers': sum(1 for qr in question_results if qr['is_correct'])
    }
    
    return render(request, 'subjects/quiz_attempt_detail.html', context)


# XP Chatbot API Views

class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Subject.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def upload_material(self, request, pk=None):
        subject = self.get_object()
        serializer = SubjectMaterialSerializer(data=request.data)
        
        if serializer.is_valid():
            material = serializer.save(subject=subject)
            # Trigger background processing and quiz generation
            process_material.delay(material.id)
            generate_quiz_from_material.delay(material.id, num_questions=10)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        subject = self.get_object()
        materials = SubjectMaterial.objects.filter(subject=subject)
        serializer = SubjectMaterialSerializer(materials, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def ask_question(self, request, pk=None):
        subject = self.get_object()
        question = request.data.get('question')
        if not question:
            return Response(
                {'error': 'Question is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Implement AI question answering
        return Response({'answer': 'AI answer will be implemented here'})

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
        flashcards = Flashcard.objects.filter(subject=subject)
        serializer = FlashcardSerializer(flashcards, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def quizzes(self, request, pk=None):
        """Get all quizzes for a subject"""
        subject = self.get_object()
        quizzes = Quiz.objects.filter(subject=subject)
        quiz_data = []
        
        for quiz in quizzes:
            quiz_data.append({
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

    def get_queryset(self):
        return SubjectMaterial.objects.filter(subject__user=self.request.user)

    def perform_create(self, serializer):
        material = serializer.save()
        process_material.delay(material.id)
        # Also generate quiz from the uploaded material
        generate_quiz_from_material.delay(material.id, num_questions=10)

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
            quiz = Quiz.objects.get(
                subject=material.subject,
                title__icontains=material.file.name
            )
            
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
                correct_answers = question.answers.filter(is_correct=True)
                for answer in correct_answers:
                    if answer_text.lower().strip() in answer.text.lower().strip():
                        is_correct = True
                        break
            
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
        
        try:
            # Use SessionManager for intelligent session management with timeout logic
            session_manager = SessionManager()
            session, created = session_manager.get_or_create_session(
                user=self.request.user,
                subject=subject,
                content=user_message_content  # Used for title generation
            )
            
            if created:
                logger.info(f"Created new chat session {session.id} for user {request.user.id} and subject {subject_id}")
            else:
                logger.info(f"Using existing session {session.id} for user {request.user.id} and subject {subject_id}")
            
            # Save user message
            user_message = ChatMessage.objects.create(
                session=session,
                role='user',
                content=user_message_content,
                metadata={}
            )
            
            # Get chat history for context (last 10 exchanges)
            previous_messages = ChatMessage.objects.filter(
                session=session
            ).exclude(
                id=user_message.id
            ).order_by('-timestamp')[:20]  # Get last 20 messages (10 exchanges)
            
            # Format chat history for RAG service
            chat_history = []
            messages_list = list(reversed(previous_messages))  # Reverse to chronological order
            
            for i in range(0, len(messages_list), 2):
                if i + 1 < len(messages_list):
                    if (messages_list[i].role == 'user' and 
                        messages_list[i + 1].role == 'assistant'):
                        chat_history.append({
                            'user': messages_list[i].content,
                            'assistant': messages_list[i + 1].content
                        })
            
            # Generate response using RAG service
            rag_service = RAGService()
            
            logger.info(f"Generating RAG response for user {request.user.id}, subject {subject_id}, query: {user_message_content[:100]}...")
            
            rag_response = rag_service.generate_response(
                query=user_message_content,
                subject_id=subject.id,
                chat_history=chat_history,
                user_id=request.user.id
            )
            
            # Save assistant message with metadata
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
            
            # Update session activity timestamp using SessionManager
            session_manager.extend_session(session)
            
            # Generate session title if this is the first exchange (no title yet)
            if not session.title or session.title == "New conversation":
                try:
                    title = self._generate_session_title(user_message_content, rag_response['response'], subject.name)
                    session.title = title
                    session.save(update_fields=['title'])
                    logger.info(f"Generated title for session {session.id}: {title}")
                except Exception as e:
                    logger.warning(f"Failed to generate title for session {session.id}: {str(e)}")
            
            logger.info(f"Successfully generated chat response for user {request.user.id}, session {session.id}")
            
            # Prepare response
            response_data = {
                'user_message': ChatMessageSerializer(user_message).data,
                'assistant_message': ChatMessageSerializer(assistant_message).data,
                'session': ChatSessionSerializer(session).data,
                'response_metadata': {
                    'chunks_retrieved': len(rag_response['retrieved_chunks']),
                    'response_time_seconds': rag_response['response_time'],
                    'context_was_used': rag_response['context_used']
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error generating chat response for user {request.user.id}, subject {subject_id}: {str(e)}")
            
            # Return error response
            return Response({
                'error': 'Failed to generate response',
                'message': 'XP is currently unavailable. Please try again later.',
                'details': str(e) if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_session_title(self, user_message, assistant_response, subject_name):
        """Generate a concise title for the chat session based on the first exchange."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            prompt = f"""Based on this conversation about {subject_name}, create a concise, descriptive title (max 50 characters) that captures the main topic:

User: {user_message[:200]}
Assistant: {assistant_response[:200]}

Generate a title that is:
- Specific to the topic discussed
- Maximum 50 characters
- Clear and descriptive
- No quotes or special formatting

Title:"""
            
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
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
