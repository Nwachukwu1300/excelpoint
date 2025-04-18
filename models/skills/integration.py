"""
Examples of integrating the resume parser and skill extractor into various Django contexts.

This module provides practical examples for:
1. Using the models in Django views
2. Adding skill extraction to a Django model
3. Creating a background task for batch processing
4. API integration examples
"""

import os
from django.conf import settings
from django.db import models
from django.core.files.storage import default_storage

from .resume_parser import ResumeParser
from .skill_extractor import SkillExtractor
from .django_integration import ResumeProcessingService

# Example 1: Simple function-based view integration
def extract_skills_view(request):
    """Example of a simple view to extract skills from text."""
    from django.http import JsonResponse
    
    if request.method == 'POST':
        text = request.POST.get('text', '')
        confidence = float(request.POST.get('confidence', 0.7))
        
        # Create extractor and extract skills
        extractor = SkillExtractor()
        skills = extractor.extract_skills(text)
        
        # Filter by confidence
        skills = [s for s in skills if s['confidence'] >= confidence]
        
        return JsonResponse({
            'success': True,
            'skills': skills,
            'count': len(skills)
        })
    
    return JsonResponse({'success': False, 'error': 'POST request required'})

# Example 2: Django model integration
class JobPosting(models.Model):
    """Example of a Django model with integrated skill extraction."""
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Skill-related fields
    required_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    
    def extract_skills(self):
        """Extract skills from the job description and save them."""
        if not self.description:
            return
        
        # Create processing service
        service = ResumeProcessingService()
        
        # Extract and categorize skills
        job_skills = service.get_skills_for_job_posting(self.description)
        
        # Update fields
        self.required_skills = [s['skill'] for s in job_skills['required_skills']]
        self.preferred_skills = [s['skill'] for s in job_skills['preferred_skills']]
        self.save(update_fields=['required_skills', 'preferred_skills'])
    
    def save(self, *args, **kwargs):
        """Override save to extract skills when description changes."""
        is_new = self.pk is None
        
        # Call the original save method
        super().save(*args, **kwargs)
        
        # Extract skills on new creation or if description field was updated
        if is_new or 'description' in kwargs.get('update_fields', []):
            self.extract_skills()

# Example 3: Background task integration with Celery
def process_resume_task(file_path, user_id):
    """
    Example of a Celery task for background resume processing.
    
    To use with Celery:
    
    @app.task
    def process_resume_task(file_path, user_id):
        ...
    
    Then call: process_resume_task.delay(file_path, user_id)
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Get the full path
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # Parse the resume
        parser = ResumeParser()
        result = parser.parse_file(full_path)
        
        if result['success']:
            # Get user
            user = User.objects.get(id=user_id)
            
            # Here you would update the user's profile with the extracted skills
            # For example, if your User model has a related Profile model:
            if hasattr(user, 'profile'):
                # Update profile with extracted skills
                skills_data = result['data'].get('skills', [])
                
                # Flatten skills by category into a list
                all_skills = []
                for category in skills_data:
                    all_skills.extend(category.get('skills', []))
                
                # Save to profile
                user.profile.skills = all_skills
                user.profile.save()
            
            # Save the parsing result for later reference
            json_path = f'parsed_resumes/{os.path.splitext(os.path.basename(file_path))[0]}.json'
            with default_storage.open(json_path, 'w') as f:
                import json
                json.dump(result, f, indent=2)
            
            return {
                'success': True,
                'user_id': user_id,
                'skills_count': len(all_skills),
                'result_path': json_path
            }
    
    except Exception as e:
        # Log the error
        import logging
        logging.error(f"Error processing resume {file_path}: {str(e)}")
        
        return {
            'success': False,
            'error': str(e)
        }

# Example 4: API serializer integration
def create_serializer_integration():
    """Example of integrating with Django Rest Framework serializers."""
    try:
        from rest_framework import serializers
        
        class SkillSerializer(serializers.Serializer):
            """Serializer for skill data."""
            skill = serializers.CharField()
            confidence = serializers.FloatField()
            category = serializers.CharField(required=False, allow_null=True)
            extraction_method = serializers.CharField(required=False, allow_null=True)
        
        class ResumeUploadSerializer(serializers.Serializer):
            """Serializer for resume upload and processing."""
            resume = serializers.FileField()
            extract_skills = serializers.BooleanField(default=True)
            
            def validate_resume(self, value):
                """Validate the uploaded resume file."""
                # Check file extension
                ext = os.path.splitext(value.name)[1].lower()
                if ext not in ['.pdf', '.docx', '.txt']:
                    raise serializers.ValidationError(
                        "Unsupported file format. Please upload a PDF, DOCX, or TXT file."
                    )
                
                # Check file size (max 5 MB)
                if value.size > 5 * 1024 * 1024:
                    raise serializers.ValidationError(
                        "File size exceeds 5 MB. Please upload a smaller file."
                    )
                
                return value
            
            def create(self, validated_data):
                """Process the resume and extract skills."""
                resume_file = validated_data['resume']
                extract_skills = validated_data.get('extract_skills', True)
                
                # Create processing service
                service = ResumeProcessingService()
                
                # Process the resume
                result = service.process_resume_file(resume_file, save_result=True)
                
                # Return the processing result
                return result
        
        return {
            'SkillSerializer': SkillSerializer,
            'ResumeUploadSerializer': ResumeUploadSerializer
        }
    
    except ImportError:
        # Django Rest Framework not installed
        return None 