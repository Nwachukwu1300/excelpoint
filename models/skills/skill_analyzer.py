import os
import json
from typing import List, Dict, Optional
from collections import Counter

# Import the skill extractor
from .skill_extractor import SkillExtractor

class SkillAnalyzer:
    """
    Analyzes skills from resume text and job descriptions.
    Provides skill gap analysis, recommendations, and skill categorization.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm", skills_file: str = None, min_confidence: float = 0.7):
        """
        Initialize the skill analyzer.
        
        Args:
            model_name: Name of the spaCy model to use for extraction
            skills_file: Path to a file containing skill definitions
            min_confidence: Minimum confidence threshold for skills (0.0-1.0)
        """
        # Load the skill extractor
        if skills_file and os.path.exists(skills_file):
            self.extractor = SkillExtractor.from_file(skills_file, model_name)
        else:
            self.extractor = SkillExtractor(model_name=model_name)
            
        # Set minimum confidence threshold
        self.min_confidence = min_confidence
            
        # Skill categories and their weights for scoring
        self.skill_categories = {
            'technical': 1.0,
            'soft': 0.8,
            'domain': 0.9,
            'tool': 0.7,
            'certification': 0.6,
            'unknown': 0.5
        }
    
    def analyze_resume(self, resume_text: str) -> Dict:
        """
        Extract and analyze skills from a resume.
        
        Args:
            resume_text: The text content of a resume
            
        Returns:
            Dictionary with extracted skills and analysis
        """
        # Extract skills
        all_skills = self.extractor.extract_skills(resume_text)
        
        # Filter by confidence
        skills = [skill for skill in all_skills if skill['confidence'] >= self.min_confidence]
        
        # Group skills by category
        categorized = self._categorize_skills(skills)
        
        # Calculate skill scores
        scores = self._calculate_skill_scores(skills)
        
        return {
            'skills': skills,
            'categorized_skills': categorized,
            'skill_scores': scores,
            'top_skills': self._get_top_skills(skills, 5),
            'skill_count': len(skills),
            'total_extracted': len(all_skills),
            'filtered_out': len(all_skills) - len(skills)
        }
    
    def analyze_job(self, job_description: str) -> Dict:
        """
        Extract and analyze skills from a job description.
        
        Args:
            job_description: The text content of a job posting
            
        Returns:
            Dictionary with extracted skills and requirements
        """
        # Extract skills
        all_skills = self.extractor.extract_skills(job_description)
        
        # Filter by confidence
        skills = [skill for skill in all_skills if skill['confidence'] >= self.min_confidence]
        
        # Group skills by category
        categorized = self._categorize_skills(skills)
        
        # Determine required vs preferred skills (higher confidence = required)
        required = []
        preferred = []
        
        for skill in skills:
            if skill['confidence'] >= 0.85:
                required.append(skill)
            else:
                preferred.append(skill)
        
        return {
            'skills': skills,
            'categorized_skills': categorized,
            'required_skills': required,
            'preferred_skills': preferred,
            'skill_count': len(skills),
            'total_extracted': len(all_skills),
            'filtered_out': len(all_skills) - len(skills)
        }
    
    def skill_gap_analysis(self, resume_text: str, job_description: str) -> Dict:
        """
        Perform skill gap analysis between a resume and job description.
        
        Args:
            resume_text: The text content of a resume
            job_description: The text content of a job posting
            
        Returns:
            Dictionary with skill gap analysis
        """
        # Analyze resume and job separately
        resume_analysis = self.analyze_resume(resume_text)
        job_analysis = self.analyze_job(job_description)
        
        # Get skill sets
        resume_skills = {skill['skill'].lower(): skill for skill in resume_analysis['skills']}
        job_skills = {skill['skill'].lower(): skill for skill in job_analysis['skills']}
        
        # Find matching skills
        matching_skills = []
        for skill_name, skill_data in resume_skills.items():
            if skill_name in job_skills:
                matching_skills.append({
                    'skill': skill_data['skill'],
                    'resume_confidence': skill_data['confidence'],
                    'job_confidence': job_skills[skill_name]['confidence']
                })
        
        # Find critical missing skills (only high confidence required skills from the job)
        critical_missing_skills = []
        for skill_name, skill_data in job_skills.items():
            if skill_name not in resume_skills and skill_data['confidence'] >= 0.85:
                critical_missing_skills.append(skill_data)
        
        # Calculate match score (0-100)
        # This is the percentage of required skills in the job that are matched in the resume
        if not job_analysis['required_skills']:
            # If no specific required skills, base on overall matching
            if not job_skills:
                match_score = 0
            else:
                match_score = (len(matching_skills) / len(job_skills)) * 100
        else:
            # Count matches for required skills
            required_job_skills = {s['skill'].lower() for s in job_analysis['required_skills']}
            matched_required = sum(1 for skill in matching_skills 
                                 if skill['skill'].lower() in required_job_skills)
            
            # Base 80% of score on matching required skills
            if len(required_job_skills) > 0:
                req_score = (matched_required / len(required_job_skills)) * 80
            else:
                req_score = 0
                
            # Remaining 20% on matching any skills
            if len(job_skills) > len(required_job_skills) and len(job_skills) > 0:
                other_score = (len(matching_skills) - matched_required) / (len(job_skills) - len(required_job_skills)) * 20
            else:
                other_score = 0
                
            match_score = req_score + other_score
            
        # Cap at 100
        match_score = min(match_score, 100)
        
        return {
            'matching_skills': matching_skills,
            'critical_missing_skills': critical_missing_skills,
            'match_score': match_score,
            'match_explanation': self._generate_match_explanation(match_score, matching_skills, critical_missing_skills),
            'resume_analysis': {
                'top_skills': resume_analysis['top_skills'],
                'skill_count': resume_analysis['skill_count']
            },
            'job_analysis': {
                'required_skills': job_analysis['required_skills'],
                'preferred_skills': job_analysis['preferred_skills'],
                'skill_count': job_analysis['skill_count']
            }
        }
    
    def _generate_match_explanation(self, match_score: float, matching_skills: List[Dict], missing_skills: List[Dict]) -> str:
        """Generate a human-readable explanation of the match score."""
        if match_score >= 90:
            return "Excellent match! Your skills align very well with the job requirements."
        elif match_score >= 75:
            return "Strong match. You have most of the key skills required for this position."
        elif match_score >= 50:
            return f"Moderate match. You have {len(matching_skills)} matching skills, but are missing {len(missing_skills)} critical skills."
        elif match_score >= 25:
            return "Below average match. You may need to develop several key skills for this role."
        else:
            return "Low match. This position requires many skills not found in your profile."
    
    def recommend_skills(self, resume_text: str, target_job_type: str = None) -> List[Dict]:
        """
        Recommend skills to learn based on resume content and optional target job.
        
        Args:
            resume_text: The text content of a resume
            target_job_type: Optional job type/title to target recommendations
            
        Returns:
            List of recommended skills with reasons
        """
        # Simple implementation - in a real system, this would use a database of skills
        # or ML model to make recommendations based on the industry and job market
        
        # Extract current skills
        resume_analysis = self.analyze_resume(resume_text)
        current_skills = {skill['skill'].lower() for skill in resume_analysis['skills']}
        
        # Define some common skill combinations/relationships
        # This would normally come from a database or ML model
        skill_relationships = {
            'python': ['django', 'flask', 'fastapi', 'pandas', 'numpy', 'scikit-learn'],
            'javascript': ['react', 'vue', 'angular', 'node.js', 'express'],
            'java': ['spring', 'hibernate', 'junit', 'maven'],
            'data science': ['python', 'r', 'sql', 'machine learning', 'data visualization'],
            'devops': ['docker', 'kubernetes', 'jenkins', 'terraform', 'aws'],
            'web development': ['html', 'css', 'javascript', 'react', 'node.js']
        }
        
        recommendations = []
        
        # Look for skills that complement existing skills
        for skill, related_skills in skill_relationships.items():
            if skill.lower() in current_skills:
                for related in related_skills:
                    if related.lower() not in current_skills:
                        recommendations.append({
                            'skill': related,
                            'reason': f"Complements your knowledge of {skill}",
                            'confidence': 0.8
                        })
        
        # Sort by confidence and return top 5
        return sorted(recommendations, key=lambda x: x['confidence'], reverse=True)[:5]
    
    def _categorize_skills(self, skills: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group skills by category.
        
        Args:
            skills: List of extracted skills
            
        Returns:
            Dictionary with skills grouped by category
        """
        categorized = {}
        
        for skill in skills:
            category = skill.get('category', 'unknown')
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(skill)
        
        return categorized
    
    def _calculate_skill_scores(self, skills: List[Dict]) -> Dict[str, float]:
        """
        Calculate normalized scores for skills by category.
        
        Args:
            skills: List of extracted skills
            
        Returns:
            Dictionary with category scores
        """
        # Count skills by category
        counts = Counter([skill.get('category', 'unknown') for skill in skills])
        
        # Calculate weighted scores
        scores = {}
        total = sum(counts.values())
        
        if total > 0:
            for category, count in counts.items():
                weight = self.skill_categories.get(category, 0.5)
                scores[category] = (count / total) * weight * 100
        
        return scores
    
    def _get_top_skills(self, skills: List[Dict], limit: int = 5) -> List[Dict]:
        """
        Get the top skills by confidence.
        
        Args:
            skills: List of extracted skills
            limit: Maximum number of skills to return
            
        Returns:
            List of top skills
        """
        return sorted(skills, key=lambda x: x['confidence'], reverse=True)[:limit]


if __name__ == "__main__":
    # Example usage
    sample_resume = """
    Experienced Software Engineer with 5 years of experience in Python, Django, and JavaScript.
    Developed RESTful APIs and worked with React for frontend development.
    Strong problem-solving and communication skills with a focus on delivering high-quality code.
    Familiar with AWS, Docker, and CI/CD workflows.
    """
    
    sample_job = """
    Senior Software Engineer - Python
    
    Requirements:
    - 5+ years of experience with Python and web frameworks (Django, Flask)
    - Strong knowledge of RESTful APIs and microservices architecture
    - Experience with React or Angular
    - Excellent problem-solving and communication skills
    - CI/CD experience
    
    Nice to have:
    - Experience with AWS or Azure
    - Knowledge of Docker and Kubernetes
    - Experience with TDD methodology
    """
    
    analyzer = SkillAnalyzer()
    
    # Perform skill gap analysis
    gap_analysis = analyzer.skill_gap_analysis(sample_resume, sample_job)
    
    # Print results
    print("\nSkill Gap Analysis:")
    print(f"Match Score: {gap_analysis['match_score']:.1f}%")
    
    print("\nMatching Skills:")
    for skill in gap_analysis['matching_skills']:
        print(f"- {skill['skill']}")
    
    print("\nCritical Missing Skills:")
    for skill in gap_analysis['critical_missing_skills']:
        print(f"- {skill['skill']}")
    
    # Get recommendations
    recommendations = analyzer.recommend_skills(sample_resume)
    
    print("\nSkill Recommendations:")
    for rec in recommendations:
        print(f"- {rec['skill']}: {rec['reason']}") 