from rest_framework import serializers
from .models import Subject, SubjectMaterial, ContentChunk, Flashcard, QuizQuestion, QuizAttempt

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