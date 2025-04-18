import os
import json
import re
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .resume_parser import ResumeParser
from .skill_extractor import SkillExtractor

# Import the Skill model
from skills.models import Skill

class ResumeProcessingService:
    """Service for processing resume files within Django."""
    
    def __init__(self):
        """Initialize the resume processing service."""
        self.parser = ResumeParser()
        self.skill_extractor = SkillExtractor()
        # Ensure required directories exist
        self._ensure_media_dirs()
    
    def _ensure_media_dirs(self):
        """Ensure media directories exist."""
        media_dirs = [
            'temp_resumes',
            'parsed_resumes'
        ]
        for directory in media_dirs:
            dir_path = os.path.join(settings.MEDIA_ROOT, directory)
            os.makedirs(dir_path, exist_ok=True)
    
    def process_resume_file(self, file_obj, save_result=False):
        """
        Process a resume file uploaded through a Django form.
        
        Args:
            file_obj: A Django UploadedFile object
            save_result: Whether to save the parsing result to JSON
            
        Returns:
            Dictionary containing parsed resume information
        """
        # Ensure directories exist
        self._ensure_media_dirs()
        
        # Create a safe filename
        safe_filename = self._get_safe_filename(file_obj.name)
        
        # Save the file temporarily
        temp_path = default_storage.save(f'temp_resumes/{safe_filename}', ContentFile(file_obj.read()))
        
        try:
            # Get the full path
            temp_full_path = os.path.join(settings.MEDIA_ROOT, temp_path)
            
            # Parse the resume
            result = self.parser.parse_file(temp_full_path)
            
            # Save parsing result if requested
            if save_result and result['success']:
                json_filename = f'{os.path.splitext(safe_filename)[0]}.json'
                json_path = f'parsed_resumes/{json_filename}'
                json_full_path = os.path.join(settings.MEDIA_ROOT, json_path)
                
                # Ensure the directory exists
                os.makedirs(os.path.dirname(json_full_path), exist_ok=True)
                
                # Save the JSON file
                with open(json_full_path, 'w') as f:
                    json.dump(result, f, indent=2)
                
                result['json_path'] = json_path
            
            return result
        
        finally:
            # Clean up temporary file
            default_storage.delete(temp_path)
    
    def _get_safe_filename(self, filename):
        """Convert a filename to a safe version."""
        # Replace spaces and special characters
        safe_name = re.sub(r'[^\w\s.-]', '', filename)
        safe_name = re.sub(r'\s+', '_', safe_name)
        return safe_name
    
    def extract_skills_from_text(self, text, min_confidence=0.7):
        """
        Extract skills from text with confidence filtering.
        
        Args:
            text: Text to extract skills from
            min_confidence: Minimum confidence threshold (0.0-1.0)
            
        Returns:
            List of extracted skills above the confidence threshold
        """
        all_skills = self.skill_extractor.extract_skills(text)
        return [skill for skill in all_skills if skill['confidence'] >= min_confidence]
    
    def get_skills_for_job_posting(self, job_description):
        """
        Extract skills from a job posting with categorization.
        
        Args:
            job_description: Job posting text
            
        Returns:
            Dictionary with required and preferred skills
        """
        all_skills = self.skill_extractor.extract_skills(job_description)
        
        # Categorize skills by confidence
        required_skills = []
        preferred_skills = []
        
        for skill in all_skills:
            # Safely check confidence
            confidence = skill.get('confidence', 0)
            if confidence >= 0.85:
                required_skills.append(skill)
            elif confidence >= 0.7:
                preferred_skills.append(skill)
        
        return {
            'required_skills': required_skills,
            'preferred_skills': preferred_skills,
            'all_skills': all_skills
        }
    
    def calculate_skill_match(self, resume_text, job_description):
        """
        Calculate skill match percentage between resume and job posting.
        
        Args:
            resume_text: Candidate's resume text
            job_description: Job posting text
            
        Returns:
            Dictionary with match statistics
        """
        # Extract skills
        resume_skills = self.extract_skills_from_text(resume_text, min_confidence=0.7)
        job_skills = self.get_skills_for_job_posting(job_description)
        
        # Extract skill names (safely)
        resume_skill_names = set(s.get('skill', '').lower() for s in resume_skills if 'skill' in s)
        required_skill_names = set(s.get('skill', '').lower() for s in job_skills['required_skills'] if 'skill' in s)
        preferred_skill_names = set(s.get('skill', '').lower() for s in job_skills['preferred_skills'] if 'skill' in s)
        
        # Calculate matches
        required_matches = resume_skill_names.intersection(required_skill_names)
        preferred_matches = resume_skill_names.intersection(preferred_skill_names)
        
        # Calculate statistics - ensure we don't divide by zero
        required_match_percent = 0
        if required_skill_names:
            required_match_percent = (len(required_matches) / len(required_skill_names)) * 100
        elif len(required_matches) > 0:
            # If no required skills were found in job but we have matches
            required_match_percent = 100
            
        preferred_match_percent = 0
        if preferred_skill_names:
            preferred_match_percent = (len(preferred_matches) / len(preferred_skill_names)) * 100
        elif len(preferred_matches) > 0:
            # If no preferred skills were found in job but we have matches
            preferred_match_percent = 100
        
        # Overall match (weighted)
        if required_skill_names or preferred_skill_names:
            # If we have any skills from job posting, use weighted average
            total_weight = 0
            weighted_sum = 0
            
            if required_skill_names:
                weighted_sum += required_match_percent * 0.7
                total_weight += 0.7
                
            if preferred_skill_names:
                weighted_sum += preferred_match_percent * 0.3
                total_weight += 0.3
                
            overall_match = weighted_sum / total_weight if total_weight > 0 else 0
        else:
            # If no skills found in job posting
            overall_match = 0
        
        return {
            'overall_match': round(overall_match, 1),
            'required_match': round(required_match_percent, 1),
            'preferred_match': round(preferred_match_percent, 1),
            'matched_required_skills': list(required_matches),
            'matched_preferred_skills': list(preferred_matches),
            'missing_required_skills': list(required_skill_names - resume_skill_names),
            'missing_preferred_skills': list(preferred_skill_names - resume_skill_names)
        }
    
    def save_skills_to_user(self, user, text_or_skills, min_confidence=0.7):
        """
        Extract skills from text and save them to the user's profile.
        
        Args:
            user: Django User object
            text_or_skills: Either text to extract skills from or a list of already extracted skills
            min_confidence: Minimum confidence threshold (0.0-1.0)
            
        Returns:
            Dictionary with results of the operation
        """
        # Determine if input is text or already extracted skills
        if isinstance(text_or_skills, str):
            # Extract skills from text
            extracted_skills = self.extract_skills_from_text(text_or_skills, min_confidence)
        else:
            # Input is already extracted skills
            # Add safety check for confidence key
            extracted_skills = []
            for s in text_or_skills:
                # Skip items without 'skill' key
                if 'skill' not in s:
                    continue
                    
                if 'confidence' in s and s['confidence'] >= min_confidence:
                    extracted_skills.append(s)
                elif 'confidence' not in s:
                    # If confidence is missing, add with default confidence
                    s_copy = s.copy()
                    s_copy['confidence'] = min_confidence
                    extracted_skills.append(s_copy)
        
        # Keep track of added skills
        added_skills = []
        
        # Process each extracted skill
        for skill_data in extracted_skills:
            # Skip items without 'skill' key as a safety check
            if 'skill' not in skill_data:
                continue
                
            skill_name = skill_data['skill']
            
            # First check if the user already has this skill (either directly or via M2M)
            user_direct_skills = [s.name.lower() for s in user.user_skills_direct.all()]
            user_m2m_skills = [s.name.lower() for s in user.skills.all()]
            
            if skill_name.lower() in user_direct_skills or skill_name.lower() in user_m2m_skills:
                continue
                
            # Check if we have an existing skill with the same name but no user
            try:
                existing_skill = Skill.objects.get(name__iexact=skill_name, user__isnull=True)
                # If it exists but has no user, assign it to this user and update it
                existing_skill.user = user
                existing_skill.save()
                # Add to M2M relationship
                user.skills.add(existing_skill)
                added_skills.append(skill_name)
                continue
            except Skill.DoesNotExist:
                # Skill doesn't exist, we'll create it below
                pass
            except Skill.MultipleObjectsReturned:
                # Multiple skills with same name but no user - use the first one
                existing_skill = Skill.objects.filter(name__iexact=skill_name, user__isnull=True).first()
                existing_skill.user = user
                existing_skill.save()
                # Add to M2M relationship
                user.skills.add(existing_skill)
                added_skills.append(skill_name)
                continue
                
            # Create a new skill directly associated with this user
            skill = Skill.objects.create(
                name=skill_name,
                category=skill_data.get('category', ''),
                description=f"Extracted with confidence: {skill_data.get('confidence', min_confidence):.2f}",
                user=user  # Make sure user is explicitly set
            )
            
            # Also add to the M2M relationship for backward compatibility
            user.skills.add(skill)
            
            added_skills.append(skill_name)
        
        return {
            'success': True,
            'added_skills': added_skills,
            'total_skills': len(added_skills)
        } 