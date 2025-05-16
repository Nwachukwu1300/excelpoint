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
            'achievements': [
                r'(?i)(?:^|\n)\s*(ACHIEVEMENTS|AWARDS|HONORS|SCHOLARSHIPS|RECOGNITION|ACCOMPLISHMENTS)'
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
        
        # Education-related patterns
        self.education_patterns = {
            'degree': [
                r'(?i)(?:Bachelor|B\.?A\.?|B\.?S\.?|B\.?E\.?|Master|M\.?A\.?|M\.?S\.?|M\.?B\.?A\.?|Ph\.?D\.?|Doctorate|Associate|A\.?A\.?|A\.?S\.?|Diploma)',
                r"(?i)(?:Bachelor's|Master's|Doctoral) (?:Degree|degree)?",
                r'(?i)(?:High School|Secondary School|College|University)'
            ],
            'graduation_date': [
                r'(?i)(?:Graduated|Graduation|Completed|Earned|Received) (?:in|on)? (\w+ \d{4}|\d{4})',
                r'(?i)(\d{4})(?: ?- ?(?:\d{4}|Present|Ongoing|Current))?'
            ],
            'gpa': r'(?i)(?:GPA|Grade Point Average)[: ]? ?(\d+\.\d+)'
        }
        
        # Achievement-related patterns
        self.achievement_patterns = {
            'scholarship': [
                r'(?i)(?:Scholarship|Fellowship|Grant) (?:recipient|awarded|received)?(?: for| from| in)? (.*?)(?:\n|$)',
                r'(?i)(?:Awarded|Received|Earned|Won) (?:the |a )?(.*?)(:(?:scholarship|fellowship|grant))(.*?)(?:\n|$)'
            ],
            'award': [
                r'(?i)(?:Award|Honor|Prize|Medal|Trophy|Recognition) (?:recipient|winner|for|received)?(?: for| from| in)? (.*?)(?:\n|$)',
                r'(?i)(?:Awarded|Received|Earned|Won|Honored with) (?:the |a |an )?(.*?)(?:award|honor|prize|medal|trophy|recognition)(.*?)(?:\n|$)'
            ],
            'honor': [
                r'(?i)(?:Dean\'?s List|Honor Roll|Magna Cum Laude|Summa Cum Laude|Cum Laude)',
                r'(?i)(?:Graduated|Completed) (?:with|in) (?:honors|distinction|high distinction)'
            ]
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
        
        # Store the full text for reference by other methods
        self.full_text = text
        
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
        achievements = self._extract_achievements(sections.get('achievements', ''))
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
                'achievements': achievements,
                'projects': projects,
                'languages': languages,
                'full_text': cleaned_text  # Include full text for reference
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
        """
        Extract education information from the education section.
        
        Enhanced with contextual window approach for better recognition.
        
        Args:
            education_section: Text containing education information
            
        Returns:
            List of dictionaries containing education details
        """
        self.full_text = self.full_text if hasattr(self, 'full_text') else ""
        
        if not education_section:
            # Fall back to searching the entire resume for education
            paragraphs = re.split(r'\n\s*\n', self._clean_text(self.full_text))
            education_paragraphs = []
            
            # Education keywords to look for in the entire text
            education_indicators = [
                r'(?:bachelor|b\.?a\.?|b\.?s\.?|b\.?e\.?|master|m\.?a\.?|m\.?s\.?|m\.?b\.?a\.?|ph\.?d\.?|doctorate|associate|a\.?a\.?|a\.?s\.?|diploma)',
                r'(?:degree|university|college|school|institute|academy)',
                r'(?:graduated|graduation|completed|earned|received)\s+(?:from|in|with)',
                r'(?:major|minor|concentration|gpa)',
                r'(?:high school|secondary school)'
            ]
            
            # Search for paragraphs that might contain education
            for paragraph in paragraphs:
                for indicator in education_indicators:
                    if re.search(rf'(?i){indicator}', paragraph):
                        education_paragraphs.append(paragraph)
                        break
            
            # Use these paragraphs as our education section
            if education_paragraphs:
                education_section = "\n\n".join(education_paragraphs)
        
        # If we still don't have an education section, return empty list
        if not education_section:
            return []
        
        # Split the education section into potential entries
        paragraphs = re.split(r'\n\s*\n|(?:\r\n){2,}', education_section)
        education_entries = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Use the entire paragraph as context
            entry_text = paragraph.strip()
            lines = entry_text.split('\n')
            
            # Initialize with the full raw text for reference
            entry = {'raw_text': entry_text}
            
            # Extract degree information - try multiple approaches
            degree_found = False
            
            # First approach: Look for specific degree keywords
            for degree_pattern in self.education_patterns['degree']:
                degree_match = re.search(degree_pattern, entry_text)
                if degree_match:
                    # Window approach: Get context around the degree
                    # Look for the entire phrase containing the degree (up to period or comma)
                    degree_context = re.search(rf'(?i)([^.,\n]*{re.escape(degree_match.group(0))}[^.,\n]*)', entry_text)
                    if degree_context:
                        entry['degree'] = degree_context.group(1).strip()
                    else:
                        entry['degree'] = degree_match.group(0).strip()
                    degree_found = True
                    break
            
            # Second approach: Use the first line if it likely contains the degree
            if not degree_found and lines:
                first_line = lines[0].strip()
                # Often the first line contains the degree
                if any(keyword.lower() in first_line.lower() for keyword in ['degree', 'bachelor', 'master', 'phd', 'diploma', 'certificate']):
                    entry['degree'] = first_line
                    degree_found = True
            
            # Third approach: If still no degree, but we have a University/College, infer a degree
            if not degree_found:
                institution_match = re.search(r'(?i)(.*?(?:university|college|institute|school))', entry_text)
                if institution_match:
                    # Look for an education level/major before the institution
                    major_match = re.search(r'(?i)((?:computer science|engineering|business|arts|science|economics|psychology|education|nursing|mathematics|history|physics|chemistry|biology|marketing|finance).*?)(?:at|from|,|\n)', entry_text)
                    if major_match:
                        entry['degree'] = f"Degree in {major_match.group(1).strip()}"
                    else:
                        entry['degree'] = "Degree"
                    degree_found = True
            
            # If we still don't have a degree, use the first line as default
            if not degree_found and lines:
                entry['degree'] = lines[0].strip()
            
            # Extract institution name using multiple patterns
            institution_patterns = [
                r'(?i)(?:at|from)\s+(.*?(?:university|college|institute|school)(?:(?:\s+of\s+|\s+)[\w\s&]+)?)',
                r'(?i)((?:[A-Z][A-Za-z\']*\s+){1,4}(?:University|College|Institute|School)(?:(?:\s+of\s+|\s+)[\w\s&]+)?)',
                r'(?i)([\w\s&]+(?:University|College|Institute|School))'
            ]
            
            for pattern in institution_patterns:
                institution_match = re.search(pattern, entry_text)
                if institution_match:
                    entry['institution'] = institution_match.group(1).strip()
                    break
            
            # If we didn't find an institution but have multiple lines,
            # the second line often contains the institution
            if 'institution' not in entry and len(lines) > 1:
                second_line = lines[1].strip()
                if any(keyword.lower() in second_line.lower() for keyword in ['university', 'college', 'institute', 'school']):
                    entry['institution'] = second_line
            
            # Extract graduation date
            date_patterns = [
                r'(?i)(?:graduated|graduation|completed|earned|received)\s+(?:in|on)?\s*(\w+\s+\d{4}|\d{4})',
                r'(?i)(?:may|june|july|august|september|october|november|december|january|february|march|april)\s+\d{4}',
                r'(?i)(?:19|20)\d{2}(?:\s*-\s*(?:present|current|ongoing|now|\d{4}))?'
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, entry_text)
                if date_match:
                    entry['date'] = date_match.group(0).strip()
                    break
            
            # Extract GPA if available (expanded pattern)
            gpa_patterns = [
                r'(?i)(?:gpa|grade point average|g\.p\.a\.)(?:[:\s]+)?([0-4]\.\d{1,2})',
                r'(?i)(?:gpa|grade point average|g\.p\.a\.)[:\s]+(?:of\s+)?(\d\.\d{1,2})',
                r'(?i)(?:with|earned|achieved).*?gpa\s+(?:of\s+)?([0-4]\.\d{1,2})'
            ]
            
            for pattern in gpa_patterns:
                gpa_match = re.search(pattern, entry_text)
                if gpa_match:
                    entry['gpa'] = gpa_match.group(1).strip()
                    break
            
            # Extract additional information using keywords
            additional_info = []
            
            # Extract major/minor/concentration/focus
            for keyword in ['major', 'minor', 'concentration', 'focus', 'specialization', 'program']:
                keyword_match = re.search(f'(?i){keyword}[: ]+(.*?)(?:[.;,]|\n|$)', entry_text)
                if keyword_match:
                    additional_info.append(f"{keyword.title()}: {keyword_match.group(1).strip()}")
            
            # Extract honors, awards, achievements in education
            honor_keywords = ['honors', 'distinction', 'dean\'s list', 'cum laude', 'gpa', 'graduate', 'thesis']
            for keyword in honor_keywords:
                keyword_match = re.search(f'(?i)(?:with|received|earned).*?{keyword}.*?(?:[.;,]|\n|$)', entry_text)
                if keyword_match:
                    context = re.search(f'(?i)((?:with|received|earned)[^.;,\n]*?{keyword}[^.;,\n]*)', entry_text)
                    if context:
                        additional_info.append(context.group(1).strip())
            
            # Extract extracurricular activities
            activities_match = re.search(r'(?i)(?:activities|clubs|organizations|involved in|participated in)[: ]+(.*?)(?:[.;]|\n|$)', entry_text)
            if activities_match:
                additional_info.append(f"Activities: {activities_match.group(1).strip()}")
            
            # Join additional info if any was found
            if additional_info:
                entry['additional_info'] = '; '.join(additional_info)
            
            education_entries.append(entry)
        
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
        """
        Extract certification information from the certifications section.
        
        Enhanced to use a contextual window approach to better identify certifications.
        
        Args:
            certifications_section: Text containing certification information
            
        Returns:
            List of dictionaries containing certification details
        """
        if not certifications_section:
            # Fall back to searching the entire resume for certifications
            paragraphs = re.split(r'\n\s*\n', self._clean_text(self.full_text))
            certifications_paragraphs = []
            
            # Common certification keywords to look for in the entire text
            cert_indicators = [
                r'certif', r'licens', r'accredit', r'credential', 
                r'qualified', r'awarded', r'complete'
            ]
            
            # Search for paragraphs that might contain certifications
            for paragraph in paragraphs:
                for indicator in cert_indicators:
                    if re.search(rf'(?i){indicator}', paragraph):
                        certifications_paragraphs.append(paragraph)
                        break
            
            # Use these paragraphs as our certifications section
            if certifications_paragraphs:
                certifications_section = "\n\n".join(certifications_paragraphs)
        
        # If we still don't have a certifications section, return empty list
        if not certifications_section:
            return []
        
        # Split the certifications section into potential entries
        entries = re.split(r'\n\s*\n|•|\*|\-|\d+\.', certifications_section)
        certifications = []
        
        # Common certification keywords (expanded for better matching)
        cert_keywords = [
            'certified', 'certificate', 'certification', 'certified in', 'credential',
            'license', 'licensed', 'accredited', 'qualified', 'authorized',
            'diploma', 'completion of', 'completed'
        ]
        
        # Common certification issuers (expanded)
        common_issuers = [
            'AWS', 'Amazon Web Services', 'Microsoft', 'Google', 'Cisco', 'CompTIA', 
            'Oracle', 'PMI', 'IBM', 'Adobe', 'Salesforce', 'Red Hat', 'ISACA', 
            '(ISC)²', 'Scrum Alliance', 'Agile', 'PMP', 'ITIL', 'Coursera', 'Udemy',
            'edX', 'Pluralsight', 'LinkedIn Learning', 'Tableau', 'SAP'
        ]
        
        for entry in entries:
            # Skip empty entries
            if not entry.strip():
                continue
            
            # Window approach: Use the entire entry as context
            entry_text = entry.strip()
            
            # Initialize with default values
            cert = {'name': entry_text}
            matched = False
            
            # First pass: Look for certification keywords
            for keyword in cert_keywords:
                # Look for certification keyword with surrounding context
                pattern = rf'(?i)(?:.*?)(\b{keyword}.*?)(?:(?:from|by|issued|awarded|through|,|;)|$)'
                cert_match = re.search(pattern, entry_text)
                
                if cert_match:
                    matched = True
                    cert_name = cert_match.group(1).strip()
                    # Clean up punctuation at the end
                    cert_name = re.sub(r'[,;.]+$', '', cert_name)
                    cert['name'] = cert_name
                    
                    # Look for the issuer in the remaining text
                    remaining_text = entry_text[cert_match.end(1):]
                    issuer_match = re.search(r'(?i)(?:from|by|issued|awarded|through)\s+(.*?)(?:\s+in\s+|\s+on\s+|\d{2}/\d{2}/\d{4}|$)', remaining_text)
                    
                    if issuer_match:
                        cert['issuer'] = issuer_match.group(1).strip()
                    break
            
            # Second pass: If no match yet, check for known issuers directly
            if not matched:
                for issuer in common_issuers:
                    # Check if entry contains a known issuer
                    if re.search(rf'(?i)\b{re.escape(issuer)}\b', entry_text):
                        matched = True
                        
                        # Try to extract the full certification name with issuer
                        cert_match = re.search(rf'(?i)(.*?(?:certification|certificate|credential|qualification).*?)(?:(?:from|by|issued|awarded|through)\s+{re.escape(issuer)}|$)', entry_text)
                        
                        if cert_match:
                            cert['name'] = cert_match.group(1).strip()
                            cert['issuer'] = issuer
                        else:
                            # If no explicit certification name found, use a window around the issuer
                            window_match = re.search(rf'(?i)((?:[^.;,\n]{{1,50}}\s+)?{re.escape(issuer)}(?:\s+[^.;,\n]{{1,50}})?)', entry_text)
                            if window_match:
                                cert['name'] = window_match.group(1).strip()
                                cert['issuer'] = issuer
                        break
            
            # For certifications we found, extract additional details
            if matched:
                # Extract date
                date_match = re.search(r'(?i)(?:in|on|dated?|issued|awarded|earned|received|completed)\s+(\w+\s+\d{4}|\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{2}-\d{2}-\d{4})', entry_text)
                if date_match:
                    cert['date'] = date_match.group(1).strip()
                
                # Extract expiration if mentioned
                expiry_match = re.search(r'(?i)(?:valid until|expires|expiration|exp\.?|exp date|valid through)\s+(\w+\s+\d{4}|\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{2}-\d{2}-\d{4})', entry_text)
                if expiry_match:
                    cert['expiration'] = expiry_match.group(1).strip()
                
                # Extract credential ID if mentioned
                id_match = re.search(r'(?i)(?:credential|cert|certificate|license|id|number|#)[\s:#-]+([A-Z0-9\-]+)', entry_text)
                if id_match:
                    cert['credential_id'] = id_match.group(1).strip()
                
                certifications.append(cert)
            # If we didn't match anything but the entry contains words like "certified" or "license"
            elif any(keyword in entry_text.lower() for keyword in ['certified', 'license', 'certificate', 'credential']):
                # Get the first sentence or up to 100 characters as the name
                name_match = re.search(r'(?i)^([^.;,\n]{1,100})', entry_text)
                if name_match:
                    cert['name'] = name_match.group(1).strip()
                    certifications.append(cert)
        
        return certifications
    
    def _extract_achievements(self, achievements_section: str) -> List[Dict[str, str]]:
        """
        Extract achievements such as scholarships, awards, and honors.
        
        Enhanced with contextual window approach for better recognition.
        
        Args:
            achievements_section: Text containing achievement information
            
        Returns:
            List of dictionaries containing achievement details
        """
        self.full_text = self.full_text if hasattr(self, 'full_text') else ""
        
        if not achievements_section:
            # Fall back to searching the entire resume for achievements
            paragraphs = re.split(r'\n\s*\n', self._clean_text(self.full_text))
            achievement_paragraphs = []
            
            # Achievement keywords to look for in the entire text
            achievement_indicators = [
                r'award', r'honor', r'scholarship', r'fellowship', r'grant', 
                r'recognition', r'prize', r'medal', r'achievement', r'accomplishment', 
                r'dean\'?s list', r'honor roll', r'cum laude', r'distinction'
            ]
            
            # Search for paragraphs that might contain achievements
            for paragraph in paragraphs:
                for indicator in achievement_indicators:
                    if re.search(rf'(?i){indicator}', paragraph):
                        achievement_paragraphs.append(paragraph)
                        break
            
            # Use these paragraphs as our achievements section
            if achievement_paragraphs:
                achievements_section = "\n\n".join(achievement_paragraphs)
        
        # If we still don't have an achievements section, return empty list
        if not achievements_section:
            return []
        
        # Split the achievements section into potential entries
        entries = re.split(r'\n\s*\n|•|\*|\-|\d+\.', achievements_section)
        achievements = []
        
        for entry in entries:
            # Skip empty entries
            if not entry.strip():
                continue
            
            # Window approach: Use the entire entry as context
            entry_text = entry.strip()
            
            # Default achievement with the entire entry text
            achievement = {'title': entry_text, 'type': 'general'}
            
            # Check for scholarship patterns
            scholarship_patterns = [
                r'(?i)(?:received|awarded|earned|won)(?:[^.;,\n]*?)(?:scholarship|fellowship|grant)',
                r'(?i)(?:scholarship|fellowship|grant)(?:[^.;,\n]*?)(?:recipient|awardee)',
                r'(?i)(?:full|partial|merit|academic|research)(?:[^.;,\n]*?)(?:scholarship|fellowship|grant)'
            ]
            
            for pattern in scholarship_patterns:
                if re.search(pattern, entry_text):
                    # Try to extract the full scholarship name
                    name_match = re.search(r'(?i)((?:(?:the|a|an)\s+)?[^.;,\n]{1,100}(?:scholarship|fellowship|grant))', entry_text)
                    if name_match:
                        achievement['title'] = name_match.group(1).strip()
                    achievement['type'] = 'scholarship'
                    break
            
            # Check for award patterns if not already identified as scholarship
            if achievement['type'] == 'general':
                award_patterns = [
                    r'(?i)(?:received|awarded|earned|won)(?:[^.;,\n]*?)(?:award|prize|medal|honor|recognition)',
                    r'(?i)(?:award|prize|medal|honor)(?:[^.;,\n]*?)(?:recipient|winner)',
                    r'(?i)(?:1st|2nd|3rd|first|second|third)(?:[^.;,\n]*?)(?:place|prize|position)'
                ]
                
                for pattern in award_patterns:
                    if re.search(pattern, entry_text):
                        # Try to extract the full award name
                        name_match = re.search(r'(?i)((?:(?:the|a|an)\s+)?[^.;,\n]{1,100}(?:award|prize|medal|honor|recognition))', entry_text)
                        if name_match:
                            achievement['title'] = name_match.group(1).strip()
                        achievement['type'] = 'award'
                        break
            
            # Check for honor patterns if not already identified
            if achievement['type'] == 'general':
                honor_patterns = [
                    r'(?i)dean\'?s list',
                    r'(?i)honor roll',
                    r'(?i)(?:magna|summa|)?\s*cum laude',
                    r'(?i)with (?:high |highest )?(?:honors|distinction)',
                    r'(?i)valedictorian',
                    r'(?i)salutatorian'
                ]
                
                for pattern in honor_patterns:
                    honor_match = re.search(pattern, entry_text)
                    if honor_match:
                        # Use the honor term and its immediate context
                        context_match = re.search(r'(?i)((?:[^.;,\n]{0,30}\s+)?(?:' + pattern.replace('(?i)', '') + r')(?:\s+[^.;,\n]{0,30})?)', entry_text)
                        if context_match:
                            achievement['title'] = context_match.group(1).strip()
                        else:
                            achievement['title'] = honor_match.group(0).strip()
                        achievement['type'] = 'honor'
                        break
            
            # For achievements we've identified, extract additional details
            if achievement['type'] != 'general' or any(keyword in entry_text.lower() for keyword in ['award', 'honor', 'scholarship', 'recognition', 'achievement']):
                # If we still have a long title, try to shorten it to just the first sentence or clause
                if len(achievement['title']) > 100:
                    first_part = re.search(r'^([^.;,\n]{1,100})', achievement['title'])
                    if first_part:
                        achievement['title'] = first_part.group(1).strip()
                
                # Extract date if available
                date_match = re.search(r'(?i)(?:in|on|dated?|received|awarded|earned|won)\s+(\w+\s+\d{4}|\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{2}-\d{2}-\d{4})', entry_text)
                if date_match:
                    achievement['date'] = date_match.group(1).strip()
                
                # Extract organization if mentioned
                org_match = re.search(r'(?i)(?:from|by|at|through)\s+((?:[A-Z][A-Za-z\']*(?:\s+|,\s*)){1,5})', entry_text)
                if org_match:
                    achievement['organization'] = org_match.group(1).strip()
                
                # Add a description if there's significant remaining text
                if len(entry_text) > len(achievement['title']) + 30:
                    achievement['description'] = entry_text.strip()
                
                achievements.append(achievement)
        
        return achievements
    
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