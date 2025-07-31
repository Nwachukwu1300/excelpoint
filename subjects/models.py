from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.core.files.storage import default_storage
from django.conf import settings

User = get_user_model()

class FileStorageMixin:
    """Mixin to handle file storage operations"""
    
    def save_file(self, file_obj, path):
        """Save file using the configured storage service"""
        from .services.storage_factory import StorageFactory
        storage_service = StorageFactory.get_storage_service()
        return storage_service.save_file(file_obj, path)
    
    def get_file_url(self, path):
        """Get file URL using the configured storage service"""
        from .services.storage_factory import StorageFactory
        storage_service = StorageFactory.get_storage_service()
        return storage_service.get_file_url(path)
    
    def delete_file(self, path):
        """Delete file using the configured storage service"""
        from .services.storage_factory import StorageFactory
        storage_service = StorageFactory.get_storage_service()
        storage_service.delete_file(path)

def get_storage_backend():
    """Get the appropriate storage backend based on settings"""
    if getattr(settings, 'STORAGE_BACKEND', 'local') == 's3':
        from storages.backends.s3boto3 import S3Boto3Storage
        return S3Boto3Storage()
    else:
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()

class Subject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class SubjectMaterial(models.Model):
    FILE_TYPES = (
        ('PDF', 'PDF Document'),
        ('DOCX', 'Word Document'),
        ('DOC', 'Word Document (Legacy)'),
        ('VIDEO', 'Video File'),
        ('AUDIO', 'Audio File'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='materials')
    file = models.FileField(
        upload_to='subject_materials/',
        storage=get_storage_backend(),
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'doc', 'mp4', 'mov', 'avi', 'mp3', 'wav', 'm4a'])]
    )
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.file.name} - {self.subject.name}"
    

    


class ContentChunk(models.Model):
    EMBEDDING_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    material = models.ForeignKey(SubjectMaterial, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.IntegerField()
    embedding_vector = models.JSONField(null=True, blank=True)  # Store vector embeddings for AI search
    embedding_status = models.CharField(
        max_length=10, 
        choices=EMBEDDING_STATUS_CHOICES, 
        default='pending',
        help_text="Status of embedding generation for this chunk"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['chunk_index']
        unique_together = ['material', 'chunk_index']
        indexes = [
            models.Index(fields=['embedding_status']),
            models.Index(fields=['material', 'embedding_status']),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} - {self.material.file.name} ({self.embedding_status})"
    
    def has_embedding(self):
        """Check if chunk has a valid embedding vector"""
        return self.embedding_vector is not None and len(self.embedding_vector) > 0
    
    def mark_embedding_completed(self):
        """Mark embedding as completed and update timestamp"""
        self.embedding_status = 'completed'
        self.save(update_fields=['embedding_status', 'updated_at'])
    
    def mark_embedding_failed(self):
        """Mark embedding as failed and update timestamp"""
        self.embedding_status = 'failed'
        self.save(update_fields=['embedding_status', 'updated_at'])

class Flashcard(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='flashcards')
    material = models.ForeignKey(SubjectMaterial, on_delete=models.CASCADE, related_name='flashcards', null=True, blank=True)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Flashcard: {self.question[:50]}..."

# Enhanced Quiz Models
class Quiz(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    material = models.ForeignKey(SubjectMaterial, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True, help_text="The material this quiz was generated from")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    time_limit = models.IntegerField(help_text="Time limit in minutes", null=True, blank=True)
    pass_score = models.FloatField(default=60.0, help_text="Passing score in percentage")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.subject.name}"

    def get_total_points(self):
        return sum(question.points for question in self.questions.all())

class Question(models.Model):
    QUESTION_TYPES = (
        ('multiple_choice', 'Multiple Choice'),
        ('short_answer', 'Short Answer'),
        ('true_false', 'True/False'),
    )
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    explanation = models.TextField(blank=True, help_text="Explanation for the correct answer")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ['quiz', 'order']

    def __str__(self):
        return f"{self.quiz.title} - Question {self.order}: {self.text[:50]}..."

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.text} ({'Correct' if self.is_correct else 'Incorrect'})"

class Answer(models.Model):
    """Model for storing correct answers for short answer and true/false questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    is_correct = models.BooleanField(default=True)

    def __str__(self):
        return f"Answer for {self.question.text[:30]}..."

class UserQuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    total_points = models.IntegerField(default=0)
    earned_points = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    
    # New field to store dynamic questions for this specific attempt
    dynamic_questions = models.JSONField(
        null=True, 
        blank=True, 
        help_text="Stores dynamically generated questions for this attempt"
    )
    
    # Track if this attempt uses dynamic questions
    uses_dynamic_questions = models.BooleanField(
        default=False,
        help_text="True if this attempt uses dynamically generated questions"
    )

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"

    def calculate_score(self):
        """Calculate the score for this quiz attempt"""
        if self.uses_dynamic_questions and self.dynamic_questions:
            # Calculate score for dynamic questions
            self.total_points = sum(q.get('points', 1) for q in self.dynamic_questions)
            
            # For dynamic questions, we need to get points from the dynamic_questions data
            # since answer.question is None for dynamic questions
            self.earned_points = 0
            correct_answers = self.user_answers.filter(is_correct=True)
            
            # Since we can't rely on answer.question.points for dynamic questions,
            # we'll assign points based on the dynamic questions structure
            for answer in correct_answers:
                # For dynamic questions, all questions have the same points (usually 1)
                # We can get this from the first question in dynamic_questions
                if self.dynamic_questions:
                    points_per_question = self.dynamic_questions[0].get('points', 1)
                    self.earned_points += points_per_question
        else:
            # Calculate score for static questions (original logic)
            self.total_points = sum(question.points for question in self.quiz.questions.all())
            self.earned_points = sum(
                answer.question.points for answer in self.user_answers.filter(is_correct=True)
            )
        
        if self.total_points > 0:
            self.score = (self.earned_points / self.total_points) * 100
        else:
            self.score = 0.0
        self.save()
        return self.score

    def is_passed(self):
        """Check if the user passed the quiz"""
        return self.score >= self.quiz.pass_score if self.score is not None else False

    def complete_attempt(self):
        """Mark the attempt as completed and calculate final score"""
        self.end_time = timezone.now()
        self.is_completed = True
        self.calculate_score()
        self.save()
        
    def get_questions(self):
        """Get questions for this attempt - either dynamic or static"""
        if self.uses_dynamic_questions and self.dynamic_questions:
            return self.dynamic_questions
        else:
            # Return static questions from the quiz
            return [
                {
                    'id': q.id,
                    'text': q.text,
                    'type': q.question_type,
                    'points': q.points,
                    'explanation': q.explanation,
                    'choices': [
                        {
                            'id': c.id,
                            'text': c.text,
                            'order': c.order
                        }
                        for c in q.choices.all().order_by('order')
                    ] if q.question_type in ['multiple_choice', 'true_false'] else []
                }
                for q in self.quiz.questions.all().order_by('order')
            ]

class UserAnswer(models.Model):
    attempt = models.ForeignKey(UserQuizAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True)  # Allow null for dynamic questions
    answer_text = models.TextField(blank=True, null=True)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['attempt', 'question']

    def __str__(self):
        return f"Answer by {self.attempt.user.username} for {self.question.text[:30]}..."

    def check_answer(self):
        """Check if the user's answer is correct based on question type"""
        if self.question.question_type == 'multiple_choice':
            if self.selected_choice:
                self.is_correct = self.selected_choice.is_correct
        elif self.question.question_type == 'short_answer':
            if self.answer_text:
                correct_answers = self.question.answers.values_list('text', flat=True)
                # Case-insensitive comparison and strip whitespace
                user_answer = self.answer_text.lower().strip()
                self.is_correct = any(
                    user_answer == correct_answer.lower().strip() 
                    for correct_answer in correct_answers
                )
        elif self.question.question_type == 'true_false':
            if self.selected_choice:
                self.is_correct = self.selected_choice.is_correct
        
        self.save()
        return self.is_correct

# Legacy models (keeping for backwards compatibility)
# XP Chatbot Models
class ChatSession(models.Model):
    """Model for managing XP chat sessions per user per subject"""
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('archived', 'Archived'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True, null=True, help_text="Optional session title")
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    last_activity = models.DateTimeField(default=timezone.now, help_text="Last activity timestamp for timeout tracking")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        # Removed unique_together constraint - multiple sessions allowed, only one active
        indexes = [
            models.Index(fields=['user', 'subject']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['user', 'subject', 'is_active']),  # For finding active sessions
        ]

    def __str__(self):
        return f"Chat: {self.user.username} - {self.subject.name}"

    def get_message_count(self):
        """Get total number of messages in this session"""
        return self.messages.count()

    def get_last_message(self):
        """Get the most recent message in this session"""
        return self.messages.first()
    
    def is_expired(self, timeout_minutes=5):
        """Check if session has expired based on last_activity"""
        from django.utils import timezone
        from datetime import timedelta
        
        if not self.last_activity:
            return False
            
        timeout_threshold = timezone.now() - timedelta(minutes=timeout_minutes)
        return self.last_activity < timeout_threshold
    
    def extend_session(self):
        """Update last_activity to current time to extend session"""
        from django.utils import timezone
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def expire_session(self):
        """Mark session as expired and inactive"""
        self.status = 'expired'
        self.is_active = False
        self.save(update_fields=['status', 'is_active'])

class ChatMessage(models.Model):
    """Model for storing individual chat messages in XP sessions"""
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Store context info like retrieved chunks, response time, etc."
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.role}: {content_preview}"

    def get_retrieved_chunks(self):
        """Extract retrieved chunk information from metadata"""
        return self.metadata.get('retrieved_chunks', [])

    def get_response_time(self):
        """Get response generation time from metadata"""
        return self.metadata.get('response_time', None)

class QuizQuestion(models.Model):
    """Legacy model - keeping for backwards compatibility"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='legacy_quiz_questions')
    material = models.ForeignKey(SubjectMaterial, on_delete=models.CASCADE, related_name='legacy_quiz_questions', null=True, blank=True)
    question = models.TextField()
    correct_answer = models.CharField(max_length=255)
    options = models.JSONField()  # Store multiple choice options
    hint = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Legacy Quiz: {self.question[:50]}..."

class QuizAttempt(models.Model):
    """Legacy model - keeping for backwards compatibility"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='legacy_quiz_attempts')
    quiz_question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='attempts')
    selected_answer = models.CharField(max_length=255)
    used_hint = models.BooleanField(default=False)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Legacy Attempt by {self.user.username} on {self.quiz_question.question[:30]}..."

class CachedResponse(models.Model):
    """
    Model for caching AI chatbot responses to reduce OpenAI API costs and improve performance.
    Stores responses with intelligent cache keys based on user, subject, and question.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cached_responses')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='cached_responses')
    question_hash = models.CharField(
        max_length=64, 
        help_text="MD5 hash of normalized question text"
    )
    question_text = models.TextField(
        help_text="Original question text for debugging and analytics"
    )
    response_data = models.JSONField(
        help_text="Complete RAG response data including response, metadata, and retrieved chunks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="When this cache entry expires and should be cleaned up"
    )
    hit_count = models.IntegerField(
        default=0,
        help_text="Number of times this cached response has been accessed"
    )
    last_accessed = models.DateTimeField(
        auto_now=True,
        help_text="Last time this cache entry was accessed"
    )

    class Meta:
        ordering = ['-last_accessed']
        unique_together = ['user', 'subject', 'question_hash']
        indexes = [
            models.Index(fields=['user', 'subject', 'question_hash']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['hit_count']),
            models.Index(fields=['last_accessed']),
        ]
        verbose_name = "Cached Response"
        verbose_name_plural = "Cached Responses"

    def __str__(self):
        question_preview = self.question_text[:50] + "..." if len(self.question_text) > 50 else self.question_text
        return f"Cache: {self.user.username} - {self.subject.name} - {question_preview}"

    def is_expired(self):
        """Check if this cache entry has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def increment_hit_count(self):
        """Increment the hit count and update last_accessed"""
        self.hit_count += 1
        self.save(update_fields=['hit_count', 'last_accessed'])

    def get_response_content(self):
        """Extract the main response content from response_data"""
        return self.response_data.get('response', '')

    def get_retrieved_chunks(self):
        """Extract retrieved chunks from response_data"""
        return self.response_data.get('retrieved_chunks', [])

    def get_metadata(self):
        """Extract metadata from response_data"""
        return self.response_data.get('metadata', {})

    @classmethod
    def generate_question_hash(cls, question_text):
        """Generate MD5 hash for normalized question text"""
        import hashlib
        normalized = question_text.lower().strip()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    @classmethod
    def get_cache_key(cls, user_id, subject_id, question_text):
        """Generate cache key for lookup"""
        question_hash = cls.generate_question_hash(question_text)
        return f"{user_id}:{subject_id}:{question_hash}"
