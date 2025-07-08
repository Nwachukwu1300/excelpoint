from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Subject, SubjectMaterial, Flashcard, QuizQuestion, QuizAttempt,
    Quiz, Question, Choice, Answer, UserQuizAttempt, UserAnswer
)
from .serializers import (
    SubjectSerializer, SubjectMaterialSerializer, FlashcardSerializer,
    QuizQuestionSerializer, QuizAttemptSerializer, QuizAnswerSerializer
)
from .tasks import process_material, generate_quiz_from_material, generate_dynamic_quiz_questions
import json
import os
from django.utils import timezone
from django.db import models
from django.db.models import Avg, Max

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
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            try:
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
                
                # Create the material
                material = SubjectMaterial.objects.create(
                    subject=subject,
                    file=uploaded_file,
                    file_type=file_type,
                    status='PENDING'
                )
                
                # Trigger background processing for material and quiz generation
                try:
                    process_material.delay(material.id)
                    # Also generate quiz from the uploaded material
                    generate_quiz_from_material.delay(material.id, num_questions=10)
                except Exception as e:
                    # If Celery is not running, just log the error
                    print(f"Background processing failed: {e}")
                
                messages.success(request, f'Material "{uploaded_file.name}" uploaded successfully! Quiz generation started.')
                return redirect('subject_detail', pk=pk)
                
            except Exception as e:
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
    """Display user's quiz attempt history with filtering and statistics"""
    # Get all quiz attempts for the current user
    attempts = UserQuizAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('quiz', 'quiz__subject').prefetch_related('user_answers')
    
    # Apply filters if provided
    subject_id = request.GET.get('subject')
    quiz_id = request.GET.get('quiz')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if subject_id:
        attempts = attempts.filter(quiz__subject_id=subject_id)
    
    if quiz_id:
        attempts = attempts.filter(quiz_id=quiz_id)
    
    if date_from:
        attempts = attempts.filter(start_time__date__gte=date_from)
    
    if date_to:
        attempts = attempts.filter(start_time__date__lte=date_to)
    
    # Calculate statistics
    total_attempts = attempts.count()
    avg_score = attempts.aggregate(avg_score=models.Avg('score'))['avg_score'] or 0
    best_score = attempts.aggregate(max_score=models.Max('score'))['max_score'] or 0
    
    # Get subject performance
    subject_stats = attempts.values('quiz__subject__name').annotate(
        avg_score=models.Avg('score'),
        attempt_count=models.Count('id')
    ).order_by('-avg_score')
    
    # Get recent attempts
    recent_attempts = attempts.order_by('-start_time')[:10]
    
    # Get all subjects and quizzes for filtering
    user_subjects = Subject.objects.filter(user=request.user)
    user_quizzes = Quiz.objects.filter(subject__user=request.user)
    
    context = {
        'attempts': recent_attempts,
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 1),
        'best_score': round(best_score, 1),
        'subject_stats': subject_stats,
        'user_subjects': user_subjects,
        'user_quizzes': user_quizzes,
        'filters': {
            'subject_id': subject_id,
            'quiz_id': quiz_id,
            'date_from': date_from,
            'date_to': date_to,
        }
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

# API Views
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
