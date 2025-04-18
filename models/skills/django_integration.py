import os
import json
import re
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .resume_parser import ResumeParser
from .skill_extractor import SkillExtractor

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
            if skill['confidence'] >= 0.85:
                required_skills.append(skill)
            elif skill['confidence'] >= 0.7:
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
        
        # Extract skill names
        resume_skill_names = set(s['skill'].lower() for s in resume_skills)
        required_skill_names = set(s['skill'].lower() for s in job_skills['required_skills'])
        preferred_skill_names = set(s['skill'].lower() for s in job_skills['preferred_skills'])
        
        # Calculate matches
        required_matches = resume_skill_names.intersection(required_skill_names)
        preferred_matches = resume_skill_names.intersection(preferred_skill_names)
        
        # Calculate statistics
        required_match_percent = (len(required_matches) / max(len(required_skill_names), 1)) * 100
        preferred_match_percent = (len(preferred_matches) / max(len(preferred_skill_names), 1)) * 100
        
        # Overall match (weighted)
        overall_match = (required_match_percent * 0.7) + (preferred_match_percent * 0.3)
        
        return {
            'overall_match': round(overall_match, 1),
            'required_match': round(required_match_percent, 1),
            'preferred_match': round(preferred_match_percent, 1),
            'matched_required_skills': list(required_matches),
            'matched_preferred_skills': list(preferred_matches),
            'missing_required_skills': list(required_skill_names - resume_skill_names),
            'missing_preferred_skills': list(preferred_skill_names - resume_skill_names)
        } 