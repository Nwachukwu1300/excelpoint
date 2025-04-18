import os
import sys
import json

# Fix the import to use the local module
from models.skills.resume_parser import ResumeParser

def test_parser():
    """Test the resume parser with different file types."""
    parser = ResumeParser()
    
    print("Resume Parser Test")
    print("=================")
    
    # Test capabilities
    print(f"PDF Support: {'Available' if PDF_SUPPORT else 'Not Available'}")
    print(f"DOCX Support: {'Available' if DOCX_SUPPORT else 'Not Available'}")
    
    # Path to the sample resume
    sample_resume_path = os.path.join(os.getcwd(), 'sample_resume.txt')
    
    if os.path.exists(sample_resume_path):
        print(f"\nTesting with sample resume: {sample_resume_path}")
        result = parser.parse_file(sample_resume_path)
        
        if result['success']:
            print("Parsing successful!")
            # Print extracted skills
            if 'skills' in result['data']:
                print("\nExtracted Skills:")
                for skill_cat in result['data']['skills']:
                    print(f"  Category: {skill_cat['category']}")
                    print(f"  Skills: {', '.join(skill_cat['skills'])}")
        else:
            print(f"Parsing failed: {result['error']}")
    else:
        print(f"Sample resume not found at {sample_resume_path}")
        
        # Test with sample text
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
        
        print("\nTesting with sample text...")
        result = parser.parse(test_text)
        
        if result['success']:
            print("Parsing successful!")
            # Print extracted skills
            if 'skills' in result['data']:
                print("\nExtracted Skills:")
                for skill_cat in result['data']['skills']:
                    print(f"  Category: {skill_cat['category']}")
                    print(f"  Skills: {', '.join(skill_cat['skills'])}")
        else:
            print(f"Parsing failed: {result['error']}")
    
    # Test with PDF file if one exists
    pdf_file = os.path.join(os.getcwd(), "sample_resume.pdf")
    if os.path.exists(pdf_file) and PDF_SUPPORT:
        print(f"\nTesting with PDF file: {pdf_file}")
        result = parser.parse_file(pdf_file)
        
        if result['success']:
            print("PDF parsing successful!")
        else:
            print(f"PDF parsing failed: {result['error']}")
    
    # Test with DOCX file if one exists
    docx_file = os.path.join(os.getcwd(), "sample_resume.docx")
    if os.path.exists(docx_file) and DOCX_SUPPORT:
        print(f"\nTesting with DOCX file: {docx_file}")
        result = parser.parse_file(docx_file)
        
        if result['success']:
            print("DOCX parsing successful!")
        else:
            print(f"DOCX parsing failed: {result['error']}")

if __name__ == "__main__":
    # Import PDF and DOCX support flags
    try:
        from pdfminer.high_level import extract_text as extract_text_from_pdf
        PDF_SUPPORT = True
    except ImportError:
        PDF_SUPPORT = False
    
    try:
        import docx
        DOCX_SUPPORT = True
    except ImportError:
        DOCX_SUPPORT = False
    
    test_parser() 