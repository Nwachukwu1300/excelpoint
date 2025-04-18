import re
import os
import mimetypes
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

# Import the skill extractor
from .skill_extractor import SkillExtractor

# Import optional document parsing libraries
try:
    from pdfminer.high_level import extract_text as extract_text_from_pdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: pdfminer.six not available. PDF support is disabled.")

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("Warning: python-docx not available. DOCX support is disabled.")

class ResumeParser:
    """
    Parse resume text to extract structured information like contact details,
    education, work experience, and skills.
    """
    
    def __init__(self, skills_threshold: float = 0.7):
        """
        Initialize the resume parser.
        
        Args:
            skills_threshold: Minimum confidence threshold for skill extraction
        """
        self.skill_extractor = SkillExtractor()
        self.skills_threshold = skills_threshold
        
        # Define regex patterns for different resume sections
        self.section_patterns = {
            'contact': [
                r'(?i)(?:^|\n)\s*(CONTACT|PROFILE|PERSONAL INFO|PERSONAL INFORMATION)',
                r'(?i)(?:^|\n)\s*(EMAIL|PHONE|ADDRESS|CONTACT)'
            ],
            'summary': [
                r'(?i)(?:^|\n)\s*(SUMMARY|PROFESSIONAL SUMMARY|PROFILE|OBJECTIVE|ABOUT ME)',
            ],
            'experience': [
                r'(?i)(?:^|\n)\s*(EXPERIENCE|WORK EXPERIENCE|EMPLOYMENT|EMPLOYMENT HISTORY|WORK HISTORY|PROFESSIONAL EXPERIENCE)',
            ],
            'education': [
                r'(?i)(?:^|\n)\s*(EDUCATION|EDUCATIONAL BACKGROUND|ACADEMIC BACKGROUND|ACADEMIC HISTORY|QUALIFICATIONS)'
            ],
            'skills': [
                r'(?i)(?:^|\n)\s*(SKILLS|TECHNICAL SKILLS|CORE COMPETENCIES|AREAS OF EXPERTISE|KEY SKILLS)'
            ],
            'certifications': [
                r'(?i)(?:^|\n)\s*(CERTIFICATIONS|CERTIFICATES|PROFESSIONAL CERTIFICATIONS|LICENSES)'
            ],
            'projects': [
                r'(?i)(?:^|\n)\s*(PROJECTS|PROJECT EXPERIENCE|KEY PROJECTS)'
            ],
            'languages': [
                r'(?i)(?:^|\n)\s*(LANGUAGES|LANGUAGE PROFICIENCY)'
            ]
        }
        
        # Define patterns for specific data extraction
        self.data_patterns = {
            'email': r'[\w.+-]+@[\w-]+\.[\w.-]+',
            'phone': r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            'url': r'(?:http[s]?://)?(?:www\.)?[a-zA-Z0-9]+(?:\.[a-zA-Z]{2,})+(?:/[a-zA-Z0-9-_.~%]+)*',
            'linkedin': r'(?:http[s]?://)?(?:www\.)?linkedin\.com/in/[\w\-_]+/?',
            'github': r'(?:http[s]?://)?(?:www\.)?github\.com/[\w\-_]+/?',
            'date': r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{4}|(?:january|february|march|april|may|june|july|august|september|october|november|december) \d{4}|\d{1,2}/\d{4}|\d{4}'
        }
        
        # Register additional mime types
        mimetypes.add_type('application/pdf', '.pdf')
        mimetypes.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')
        mimetypes.add_type('application/msword', '.doc')
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse resume text into structured data.
        
        Args:
            text: The resume text to parse
            
        Returns:
            Dictionary containing parsed resume information
        """
        if not text:
            return {
                'success': False,
                'error': 'No text provided',
                'data': {}
            }
        
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Split text into sections
        sections = self._split_into_sections(cleaned_text)
        
        # Extract contact information
        contact_info = self._extract_contact_info(cleaned_text, sections.get('contact', ''))
        
        # Extract summary
        summary = self._extract_summary(sections.get('summary', ''))
        
        # Extract education
        education = self._extract_education(sections.get('education', ''))
        
        # Extract work experience
        experience = self._extract_experience(sections.get('experience', ''))
        
        # Extract skills using the skill extractor
        skills_data = self._extract_skills(cleaned_text, sections.get('skills', ''))
        
        # Extract other sections
        certifications = self._extract_certifications(sections.get('certifications', ''))
        projects = self._extract_projects(sections.get('projects', ''))
        languages = self._extract_languages(sections.get('languages', ''))
        
        # Parse result
        result = {
            'success': True,
            'data': {
                'contact_info': contact_info,
                'summary': summary,
                'education': education,
                'experience': experience,
                'skills': skills_data,
                'certifications': certifications,
                'projects': projects,
                'languages': languages
            }
        }
        
        return result
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a resume file into structured data.
        
        Args:
            file_path: Path to the resume file
            
        Returns:
            Dictionary containing parsed resume information
        """
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': f'File not found: {file_path}',
                'data': {}
            }
        
        # Determine file type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Extract text based on file type
        try:
            if mime_type == 'application/pdf':
                if not PDF_SUPPORT:
                    return {
                        'success': False,
                        'error': 'PDF parsing is not available. Install pdfminer.six package.',
                        'data': {}
                    }
                text = self._extract_text_from_pdf(file_path)
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                if not DOCX_SUPPORT:
                    return {
                        'success': False,
                        'error': 'DOCX parsing is not available. Install python-docx package.',
                        'data': {}
                    }
                text = self._extract_text_from_docx(file_path)
            else:
                # Default: try to read as text file
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
        except Exception as e:
            return {
                'success': False,
                'error': f'Error reading file: {str(e)}',
                'data': {}
            }
        
        # Parse text
        return self.parse(text)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize resume text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize newlines
        text = re.sub(r'[\r\n]+', '\n', text)
        
        return text
    
    def _split_into_sections(self, text: str) -> Dict[str, str]:
        """Split resume text into sections based on headings."""
        sections = {}
        
        # Find all section headings
        section_matches = []
        for section_name, patterns in self.section_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    section_matches.append((match.start(), match.group(), section_name))
        
        # Sort matches by position
        section_matches.sort(key=lambda x: x[0])
        
        # Extract sections
        for i, (pos, heading, section_name) in enumerate(section_matches):
            start = pos
            end = section_matches[i+1][0] if i < len(section_matches) - 1 else len(text)
            
            # Extract section text, excluding the heading
            section_text = text[start:end].strip()
            sections[section_name] = section_text
        
        return sections
    
    def _extract_contact_info(self, full_text: str, contact_section: str) -> Dict[str, str]:
        """Extract contact information from resume."""
        contact_info = {}
        
        # Use the full text since contact info can be anywhere
        # But prioritize the contact section if available
        text_to_search = contact_section if contact_section else full_text
        
        # Extract email
        email_match = re.search(self.data_patterns['email'], text_to_search)
        if email_match:
            contact_info['email'] = email_match.group().strip()
        
        # Extract phone number
        phone_match = re.search(self.data_patterns['phone'], text_to_search)
        if phone_match:
            contact_info['phone'] = phone_match.group().strip()
        
        # Extract LinkedIn URL
        linkedin_match = re.search(self.data_patterns['linkedin'], text_to_search)
        if linkedin_match:
            contact_info['linkedin'] = linkedin_match.group().strip()
        
        # Extract GitHub URL
        github_match = re.search(self.data_patterns['github'], text_to_search)
        if github_match:
            contact_info['github'] = github_match.group().strip()
        
        # Extract name (usually at the top of the resume)
        # This is a simple heuristic, might need improvement
        first_line = full_text.strip().split('\n')[0].strip()
        if len(first_line) < 40 and not re.search(r'resume|cv|curriculum', first_line.lower()):
            contact_info['name'] = first_line
        
        return contact_info
    
    def _extract_summary(self, summary_section: str) -> str:
        """Extract professional summary."""
        if not summary_section:
            return ""
        
        # Simple extraction: take the first paragraph
        paragraphs = summary_section.split('\n\n')
        if paragraphs:
            # Skip the heading if it exists
            if re.match(r'(?i)(SUMMARY|PROFESSIONAL SUMMARY|PROFILE|OBJECTIVE|ABOUT ME)', paragraphs[0]):
                return paragraphs[1] if len(paragraphs) > 1 else ""
            return paragraphs[0]
        
        return ""
    
    def _extract_education(self, education_section: str) -> List[Dict[str, str]]:
        """Extract education history."""
        if not education_section:
            return []
        
        education_entries = []
        
        # Split by line breaks and bullet points
        lines = re.split(r'\n+|•', education_section)
        
        # Process lines
        current_entry = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip the section heading
            if re.match(r'(?i)(EDUCATION|EDUCATIONAL BACKGROUND)', line):
                continue
            
            # Look for degree patterns
            degree_match = re.search(r'(?i)(Bachelor|Master|PhD|Doctor|Associate|Diploma|Certificate) (?:of|in) ([^\n,]+)', line)
            if degree_match:
                # If we already have a partial entry, save it
                if current_entry:
                    education_entries.append(current_entry)
                    current_entry = {}
                
                current_entry['degree'] = degree_match.group(0)
                
                # Try to extract field of study
                field_match = re.search(r'(?i)in ([^,\n]+)', line)
                if field_match:
                    current_entry['field'] = field_match.group(1).strip()
            
            # Look for institution
            elif not current_entry.get('institution') and re.search(r'(?i)(University|College|School|Institute)', line):
                current_entry['institution'] = line
            
            # Look for dates
            date_match = re.search(self.data_patterns['date'], line)
            if date_match and not current_entry.get('date'):
                current_entry['date'] = date_match.group(0)
            
            # If we have a substantial entry with no place to put the current line
            # assume it's additional information
            elif current_entry and 'degree' in current_entry:
                current_entry['additional_info'] = line
        
        # Add the last entry if not empty
        if current_entry:
            education_entries.append(current_entry)
        
        return education_entries
    
    def _extract_experience(self, experience_section: str) -> List[Dict[str, Any]]:
        """Extract work experience."""
        if not experience_section:
            return []
        
        experience_entries = []
        
        # Split by potential entry delimiters
        entries = re.split(r'\n\s*\n', experience_section)
        
        for entry in entries:
            if not entry.strip():
                continue
            
            # Skip the section heading
            if re.match(r'(?i)(EXPERIENCE|WORK EXPERIENCE)', entry):
                continue
            
            exp_entry = {}
            
            # Extract job title (usually first line or line with uppercase words)
            lines = entry.strip().split('\n')
            for i, line in enumerate(lines):
                # Title often appears as the first line or all caps
                if i == 0 or re.match(r'^[A-Z\s]+$', line.strip()):
                    exp_entry['title'] = line.strip()
                    break
            
            # Extract company name
            company_patterns = [
                r'(?i)at ([^\n,]+)', 
                r'(?i)(?:with|for) ([^\n,]+)',
                r'(?i)(?<=\n)([^,\n]+?)(?=,|\n)'
            ]
            
            for pattern in company_patterns:
                company_match = re.search(pattern, entry)
                if company_match:
                    exp_entry['company'] = company_match.group(1).strip()
                    break
            
            # Extract date ranges
            date_pattern = r'(?i)(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\s*(?:-|to)\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}\s*(?:-|to)\s*(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}|\d{1,2}/\d{4}\s*(?:-|to)\s*\d{1,2}/\d{4}|\d{4}\s*(?:-|to)\s*\d{4}|\d{4}\s*(?:-|to)\s*(?:Present|Current|Now)'
            date_match = re.search(date_pattern, entry)
            if date_match:
                exp_entry['date_range'] = date_match.group(0).strip()
            
            # Extract responsibilities/achievements as bullet points
            bullet_pattern = r'•\s*([^\n•]+)'
            bullets = re.findall(bullet_pattern, entry)
            if bullets:
                exp_entry['responsibilities'] = [b.strip() for b in bullets if b.strip()]
            else:
                # If no bullet points, try to extract paragraphs
                # Skip the first line (likely title or company)
                description_lines = [line.strip() for line in lines[1:] if line.strip()]
                if description_lines:
                    exp_entry['description'] = ' '.join(description_lines)
            
            if exp_entry:
                experience_entries.append(exp_entry)
        
        return experience_entries
    
    def _extract_skills(self, full_text: str, skills_section: str) -> List[Dict[str, Any]]:
        """Extract skills using skill extractor."""
        # Extract skills from the skills section if available
        if skills_section:
            extracted_skills = self.skill_extractor.extract_skills(skills_section)
        else:
            # Extract from full text otherwise
            extracted_skills = self.skill_extractor.extract_skills(full_text)
        
        # Filter by confidence threshold
        filtered_skills = [
            skill for skill in extracted_skills 
            if skill['confidence'] >= self.skills_threshold
        ]
        
        # Group by category
        categorized_skills = defaultdict(list)
        for skill in filtered_skills:
            category = skill.get('category', 'general')
            categorized_skills[category].append({
                'name': skill['skill'],
                'confidence': skill['confidence']
            })
        
        # Convert to list of categorized skills
        result = []
        for category, skills in categorized_skills.items():
            result.append({
                'category': category,
                'skills': sorted([s['name'] for s in skills])
            })
        
        return result
    
    def _extract_certifications(self, certifications_section: str) -> List[Dict[str, str]]:
        """Extract certifications."""
        if not certifications_section:
            return []
        
        certifications = []
        
        # Split by potential certification delimiters
        entries = re.split(r'\n|•', certifications_section)
        
        for entry in entries:
            entry = entry.strip()
            if not entry or re.match(r'(?i)(CERTIFICATIONS|CERTIFICATES)', entry):
                continue
            
            cert = {}
            
            # Extract certification name
            cert['name'] = entry
            
            # Extract issuer if present
            issuer_match = re.search(r'(?i)(?:from|by|issued by) ([^\n,]+)', entry)
            if issuer_match:
                cert['issuer'] = issuer_match.group(1).strip()
                # Remove the issuer part from the name
                cert['name'] = entry.replace(issuer_match.group(0), '').strip()
            
            # Extract date if present
            date_match = re.search(self.data_patterns['date'], entry)
            if date_match:
                cert['date'] = date_match.group(0)
                # Remove the date part from the name
                cert['name'] = cert['name'].replace(date_match.group(0), '').strip()
            
            # Clean up the name
            cert['name'] = re.sub(r'[,\-–—] *$', '', cert['name']).strip()
            
            certifications.append(cert)
        
        return certifications
    
    def _extract_projects(self, projects_section: str) -> List[Dict[str, str]]:
        """Extract projects."""
        if not projects_section:
            return []
        
        projects = []
        
        # Split by potential project delimiters
        entries = re.split(r'\n\s*\n', projects_section)
        
        for entry in entries:
            entry = entry.strip()
            if not entry or re.match(r'(?i)(PROJECTS|PROJECT EXPERIENCE)', entry):
                continue
            
            project = {}
            
            # Extract project name (usually first line)
            lines = entry.strip().split('\n')
            if lines:
                project['name'] = lines[0].strip()
            
            # Extract description
            if len(lines) > 1:
                project['description'] = ' '.join(lines[1:]).strip()
            
            # Extract URL if present
            url_match = re.search(self.data_patterns['url'], entry)
            if url_match:
                project['url'] = url_match.group(0)
            
            # Extract date if present
            date_match = re.search(self.data_patterns['date'], entry)
            if date_match:
                project['date'] = date_match.group(0)
            
            projects.append(project)
        
        return projects
    
    def _extract_languages(self, languages_section: str) -> List[Dict[str, str]]:
        """Extract languages."""
        if not languages_section:
            return []
        
        languages = []
        
        # Split by potential language delimiters
        entries = re.split(r'\n|•|,', languages_section)
        
        for entry in entries:
            entry = entry.strip()
            if not entry or re.match(r'(?i)(LANGUAGES|LANGUAGE PROFICIENCY)', entry):
                continue
            
            language = {}
            
            # Extract language name and proficiency
            lang_match = re.match(r'(?i)([A-Za-z]+)(?:[\s:–—-]+([A-Za-z]+))?', entry)
            if lang_match:
                language['name'] = lang_match.group(1).strip()
                if lang_match.group(2):
                    language['proficiency'] = lang_match.group(2).strip()
                
                languages.append(language)
        
        return languages
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        if not PDF_SUPPORT:
            return ""
        
        try:
            return extract_text_from_pdf(file_path)
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from a DOCX file."""
        if not DOCX_SUPPORT:
            return ""
        
        try:
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return '\n'.join(full_text)
        except Exception as e:
            print(f"Error extracting text from DOCX: {e}")
            return ""


if __name__ == "__main__":
    import json
    
    # Example usage
    parser = ResumeParser()
    
    # Sample resume text for testing
    sample_resume_path = os.path.join(os.path.dirname(__file__), 'sample_cv.txt')
    
    if os.path.exists(sample_resume_path):
        print(f"Parsing sample resume: {sample_resume_path}")
        result = parser.parse_file(sample_resume_path)
        
        # Print parsed result
        print("\nParsed Result:")
        print(json.dumps(result, indent=2))
    else:
        print(f"Sample resume not found at {sample_resume_path}")
        
        # Use a simple test string
        test_text = """
        John Smith
        Software Engineer
        
        Email: john.smith@example.com
        Phone: (555) 123-4567
        LinkedIn: linkedin.com/in/johnsmith
        
        SUMMARY
        Experienced software engineer with a passion for building scalable web applications.
        
        EXPERIENCE
        Senior Software Engineer
        ABC Company, Jan 2020 - Present
        • Led the development of a RESTful API using Django and PostgreSQL
        • Optimized database queries resulting in 30% performance improvement
        
        Software Developer
        XYZ Corp, Mar 2017 - Dec 2019
        • Developed front-end components using React and Redux
        • Collaborated with UX designers to implement responsive design
        
        EDUCATION
        Master of Science in Computer Science
        Stanford University, 2017
        
        Bachelor of Science in Computer Engineering
        MIT, 2015
        
        SKILLS
        Programming: Python, JavaScript, Java, C++
        Frameworks: Django, React, Express
        Databases: PostgreSQL, MongoDB
        Tools: Git, Docker, Jenkins
        
        CERTIFICATIONS
        AWS Certified Solutions Architect, 2021
        """
        
        result = parser.parse(test_text)
        
        # Print parsed result
        print("\nParsed Result:")
        print(json.dumps(result, indent=2)) 