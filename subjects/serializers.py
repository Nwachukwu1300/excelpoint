from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Subject, SubjectMaterial, ContentChunk, Flashcard, QuizQuestion, QuizAttempt, ChatSession, ChatMessage

User = get_user_model()

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class SubjectMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectMaterial
        fields = ['id', 'file', 'file_type', 'status', 'created_at', 'updated_at']
        read_only_fields = ['status', 'created_at', 'updated_at']

class ContentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentChunk
        fields = ['id', 'content', 'chunk_index', 'created_at']
        read_only_fields = ['created_at']

class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = ['id', 'question', 'answer', 'created_at']
        read_only_fields = ['created_at']

class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = ['id', 'question', 'options', 'hint', 'created_at']
        read_only_fields = ['created_at']

class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz_question', 'selected_answer', 'used_hint', 'is_correct', 'created_at']
        read_only_fields = ['is_correct', 'created_at']

class QuizAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_answer = serializers.CharField()
    used_hint = serializers.BooleanField(default=False)


# XP Chatbot Serializers

class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for ChatSession model with user and subject information"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    message_count = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'subject', 'user_username', 'subject_name', 
            'title', 'status', 'is_active', 'last_activity', 'created_at', 'updated_at',
            'message_count'
        ]
        read_only_fields = ['id', 'user', 'subject', 'created_at', 'updated_at', 'user_username', 'subject_name', 'last_activity']
    
    def get_message_count(self, obj):
        """Get the total number of messages in this session"""
        return obj.messages.count()
    
    def get_last_activity(self, obj):
        """Get the timestamp of the last message in this session"""
        last_message = obj.messages.order_by('-timestamp').first()
        return last_message.timestamp if last_message else obj.updated_at
    
    def validate_title(self, value):
        """Validate the session title"""
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("Title cannot be empty or only whitespace.")
        return value


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model with metadata and computed fields"""
    
    session_id = serializers.IntegerField(source='session.id', read_only=True)
    user_username = serializers.CharField(source='session.user.username', read_only=True)
    subject_name = serializers.CharField(source='session.subject.name', read_only=True)
    retrieved_chunks_count = serializers.SerializerMethodField()
    response_time_seconds = serializers.SerializerMethodField()
    has_metadata = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'session', 'session_id', 'user_username', 'subject_name',
            'role', 'content', 'timestamp', 'metadata',
            'retrieved_chunks_count', 'response_time_seconds', 'has_metadata'
        ]
        read_only_fields = [
            'id', 'timestamp', 'session_id', 'user_username', 'subject_name',
            'retrieved_chunks_count', 'response_time_seconds', 'has_metadata'
        ]
    
    def get_retrieved_chunks_count(self, obj):
        """Get the number of retrieved chunks from metadata"""
        return len(obj.get_retrieved_chunks())
    
    def get_response_time_seconds(self, obj):
        """Get response time in seconds from metadata"""
        return obj.get_response_time()
    
    def get_has_metadata(self, obj):
        """Check if message has metadata"""
        return bool(obj.metadata)
    
    def validate_role(self, value):
        """Validate the message role"""
        valid_roles = ['user', 'assistant']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Role must be one of: {', '.join(valid_roles)}")
        return value
    
    def validate_content(self, value):
        """Validate the message content"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Message content cannot be empty.")
        if len(value) > 10000:  # Reasonable limit for chat messages
            raise serializers.ValidationError("Message content is too long (max 10,000 characters).")
        return value.strip()


class ChatMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating new chat messages (user input only)"""
    
    message = serializers.CharField(max_length=10000, trim_whitespace=True)
    
    def validate_message(self, value):
        """Validate the user message"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()


class ChatHistorySerializer(serializers.Serializer):
    """Serializer for chat history with pagination and filtering options"""
    
    session = ChatSessionSerializer(read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    total_messages = serializers.IntegerField(read_only=True)
    has_more = serializers.BooleanField(read_only=True)
    
    class Meta:
        fields = ['session', 'messages', 'total_messages', 'has_more']


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response including both user and assistant messages"""
    
    user_message = ChatMessageSerializer(read_only=True)
    assistant_message = ChatMessageSerializer(read_only=True)
    session = ChatSessionSerializer(read_only=True)
    response_metadata = serializers.DictField(read_only=True)
    
    class Meta:
        fields = ['user_message', 'assistant_message', 'session', 'response_metadata'] 