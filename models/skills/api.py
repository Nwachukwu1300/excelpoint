import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

from models.skills.resume_parser import ResumeParser
from models.skills.skill_extractor import SkillExtractor

class ResumeParserAPI:
    """
    API for parsing resumes in various formats and extracting skills.
    """
    
    def __init__(self):
        """Initialize the resume parser API."""
        self.parser = ResumeParser()
        self.skill_extractor = SkillExtractor()
    
    def parse_resume(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a resume file and extract information.
        
        Args:
            file_path: Path to the resume file (PDF, DOCX, or TXT)
            
        Returns:
            Dictionary containing parsed resume information
        """
        # Verify file exists
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': f'File not found: {file_path}',
                'data': {}
            }
        
        # Parse the resume
        result = self.parser.parse_file(file_path)
        return result
    
    def extract_skills(self, text: str) -> Dict[str, Any]:
        """
        Extract skills from text.
        
        Args:
            text: Text to extract skills from
            
        Returns:
            Dictionary containing extracted skills
        """
        if not text:
            return {
                'success': False,
                'error': 'No text provided',
                'skills': []
            }
        
        # Extract skills
        skills = self.skill_extractor.extract_skills(text)
        
        # Filter by confidence
        filtered_skills = [s for s in skills if s['confidence'] >= 0.7]
        
        return {
            'success': True,
            'skills_count': len(filtered_skills),
            'skills': filtered_skills
        }

def parse_file_command(file_path: str, output_file: Optional[str] = None) -> None:
    """
    Parse a resume file and print or save the results.
    
    Args:
        file_path: Path to the resume file
        output_file: Optional path to save the output JSON
    """
    api = ResumeParserAPI()
    result = api.parse_resume(file_path)
    
    if result['success']:
        print(f"Successfully parsed: {file_path}")
        
        # Print skills summary
        if 'skills' in result['data']:
            print("\nExtracted Skills:")
            for skill_cat in result['data']['skills']:
                print(f"  Category: {skill_cat['category']}")
                print(f"  Skills: {', '.join(skill_cat['skills'])}")
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            print(f"\nFull results saved to: {output_file}")
    else:
        print(f"Error parsing resume: {result['error']}")

def main():
    """
    Command line interface for resume parsing.
    """
    parser = argparse.ArgumentParser(description='Parse resumes and extract skills')
    parser.add_argument('file', help='Path to resume file (PDF, DOCX, or TXT)')
    parser.add_argument('--output', '-o', help='Save results to this file')
    
    args = parser.parse_args()
    parse_file_command(args.file, args.output)

if __name__ == "__main__":
    main() 