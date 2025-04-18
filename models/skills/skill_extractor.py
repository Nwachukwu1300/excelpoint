import re
import os
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("Warning: spaCy not available. Using pattern-based extraction only.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available. Some features may be limited.")

from typing import List, Dict, Set, Tuple, Optional

class SkillExtractor:
    """
    Extracts skills from text using rule-based and NLP approaches.
    Compatible with Python 3.12+ and handles missing dependencies gracefully.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm", skills_list: List[str] = None):
        """
        Initialize the skill extractor.
        
        Args:
            model_name: The spaCy model to use
            skills_list: List of known skills to match against. If None, uses default patterns.
        """
        # Store known skills for matching
        self.skills_list = skills_list or []
        self.skill_aliases = {}
        
        # Try to load spaCy model, handle gracefully if not available
        self.nlp_available = False
        self.nlp = None
        
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load(model_name)
                self.nlp_available = True
                print(f"Successfully loaded spaCy model '{model_name}'")
            except Exception as e:
                print(f"Warning: Could not load spaCy model '{model_name}': {e}")
                print(f"Using pattern-based extraction only.")
                print(f"Run 'python -m spacy download {model_name}' to install.")
                
        # Load default patterns for skill matching
        self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Load default patterns for skill extraction."""
        # Technical skills patterns
        self.tech_patterns = [
            # Programming languages
            r'\b(python|java|javascript|c\+\+|ruby|go|rust|swift|kotlin|typescript|php|html|css|sql)\b',
            # Frameworks and libraries
            r'\b(django|flask|react|angular|vue|spring|laravel|express|next\.js|node\.js|rails)\b',
            # Cloud and DevOps
            r'\b(aws|azure|gcp|google cloud|kubernetes|docker|terraform|jenkins|ci/cd)\b',
            # Data science
            r'\b(machine learning|data science|deep learning|neural networks|nlp|data mining|ai)\b',
            # Databases
            r'\b(mysql|postgresql|mongodb|redis|oracle|sql server|sqlite|nosql)\b',
            # Tools and methodologies
            r'\b(git|agile|scrum|kanban|jira|devops|tdd|rest api)\b'
        ]
        
        # Soft skills patterns
        self.soft_patterns = [
            r'\b(communication|leadership|teamwork|problem[ -]solving|critical thinking)\b',
            r'\b(collaboration|adaptability|creativity|emotional intelligence|conflict resolution)\b',
            r'\b(time management|project management|decision making|analytical thinking)\b'
        ]
    
    def preprocess_text(self, text: str) -> str:
        """
        Clean and normalize text for better extraction.
        
        Args:
            text: Input text to process
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Replace newlines with spaces
        text = text.replace("\n", " ")
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_skills(self, text: str) -> List[Dict]:
        """
        Extract skills from the provided text.
        
        Args:
            text: The text to extract skills from
            
        Returns:
            List of extracted skills with metadata
        """
        if not text:
            return []
            
        # Preprocess the text
        processed_text = self.preprocess_text(text)
        
        # Extract skills using different methods
        extracted_skills = []
        
        # 1. Direct matching of known skills
        if self.skills_list:
            extracted_skills.extend(self._extract_skills_direct_match(processed_text))
        
        # 2. Pattern-based extraction (works without spaCy)
        extracted_skills.extend(self._extract_skills_pattern_based(processed_text))
        
        # 3. NLP-based extraction if available
        if self.nlp_available:
            extracted_skills.extend(self._extract_skills_nlp(processed_text))
        
        # Remove duplicates and sort by confidence
        unique_skills = self._deduplicate_skills(extracted_skills)
        
        return sorted(unique_skills, key=lambda x: x['confidence'], reverse=True)
    
    def _extract_skills_direct_match(self, text: str) -> List[Dict]:
        """
        Extract skills by directly matching against the known skills list.
        
        Args:
            text: Preprocessed text
            
        Returns:
            List of extracted skills with metadata
        """
        results = []
        
        for skill_name in self.skills_list:
            # Convert skill name to lowercase for case-insensitive matching
            skill_lower = skill_name.lower()
            
            # Check for exact match (word boundaries)
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
            matches = re.finditer(pattern, text)
            
            for match in matches:
                start, end = match.span()
                results.append({
                    'skill': skill_name,
                    'confidence': 1.0,  # High confidence for exact matches
                    'start_pos': start,
                    'end_pos': end,
                    'extraction_method': 'direct_match'
                })
                
        return results
    
    def _extract_skills_pattern_based(self, text: str) -> List[Dict]:
        """
        Extract skills using regex patterns - works without spaCy.
        
        Args:
            text: Preprocessed text
            
        Returns:
            List of extracted skills with metadata
        """
        results = []
        
        # Process all patterns
        all_patterns = self.tech_patterns + self.soft_patterns
        for i, pattern in enumerate(all_patterns):
            matches = re.finditer(pattern, text)
            for match in matches:
                start, end = match.span()
                skill_text = match.group(0)
                
                # Check if this is in our known skills list
                known_skill = False
                for db_skill in self.skills_list:
                    if db_skill.lower() == skill_text.lower():
                        skill_text = db_skill  # Use the properly cased version from DB
                        known_skill = True
                        break
                
                results.append({
                    'skill': skill_text,
                    'confidence': 0.85 if known_skill else 0.75,
                    'start_pos': start,
                    'end_pos': end,
                    'extraction_method': 'pattern_match',
                    'category': 'technical' if i < len(self.tech_patterns) else 'soft'
                })
        
        return results
    
    def _extract_skills_nlp(self, text: str) -> List[Dict]:
        """
        Extract skills using NLP techniques with spaCy.
        
        Args:
            text: Preprocessed text
            
        Returns:
            List of extracted skills with metadata
        """
        if not self.nlp_available:
            return []
            
        results = []
        
        # Process the text with spaCy
        doc = self.nlp(text)
        
        # Extract named entities that might be skills
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'GPE']:
                # Check if this entity is in our skills list
                is_known = ent.text.lower() in [s.lower() for s in self.skills_list]
                
                results.append({
                    'skill': ent.text,
                    'confidence': 0.8 if is_known else 0.6,
                    'start_pos': ent.start_char,
                    'end_pos': ent.end_char,
                    'extraction_method': 'nlp_entity',
                    'category': 'technical'  # Default category
                })
        
        # Extract noun phrases as potential skills
        for chunk in doc.noun_chunks:
            # Only consider multi-word phrases or those in skills list
            if len(chunk.text.split()) > 1 or chunk.text.lower() in [s.lower() for s in self.skills_list]:
                results.append({
                    'skill': chunk.text,
                    'confidence': 0.7 if chunk.text.lower() in [s.lower() for s in self.skills_list] else 0.5,
                    'start_pos': chunk.start_char,
                    'end_pos': chunk.end_char,
                    'extraction_method': 'nlp_noun_chunk',
                    'category': 'unknown'
                })
        
        return results
    
    def _deduplicate_skills(self, skills: List[Dict]) -> List[Dict]:
        """
        Remove duplicate skills, keeping the one with highest confidence.
        
        Args:
            skills: List of extracted skills
            
        Returns:
            Deduplicated list of skills
        """
        # Group by skill name
        skill_groups = {}
        
        for skill in skills:
            skill_name = skill['skill'].lower()
            
            if skill_name in skill_groups:
                # Keep the one with higher confidence
                if skill['confidence'] > skill_groups[skill_name]['confidence']:
                    skill_groups[skill_name] = skill
            else:
                skill_groups[skill_name] = skill
        
        return list(skill_groups.values())

    @classmethod
    def from_file(cls, file_path: str, model_name: str = "en_core_web_sm"):
        """
        Create a SkillExtractor from a file containing a list of skills.
        
        Args:
            file_path: Path to the file containing skills (one per line)
            model_name: Name of the spaCy model to use
            
        Returns:
            SkillExtractor instance
        """
        skills_list = []
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                skills_list = [line.strip() for line in f if line.strip()]
        
        return cls(model_name=model_name, skills_list=skills_list)


if __name__ == "__main__":
    # Example usage
    sample_text = """
    The ideal candidate has 5+ years of experience with Python and Django.
    They should be familiar with React, RESTful APIs, and have strong problem-solving skills.
    Experience with AWS, Docker, and CI/CD pipelines is a plus.
    Must have excellent communication and teamwork abilities.
    """
    
    # Create extractor with default patterns
    extractor = SkillExtractor()
    
    # Extract skills
    skills = extractor.extract_skills(sample_text)
    
    # Print results
    print("\nExtracted Skills:")
    for skill in skills:
        print(f"- {skill['skill']} (Confidence: {skill['confidence']:.2f}, Method: {skill['extraction_method']})") 