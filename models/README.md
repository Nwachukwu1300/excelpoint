# CareerNexus ML Models

This directory contains machine learning models used in CareerNexus for various purposes like skill extraction, job matching, and recommendations.

## Skills Module

The skills module provides tools for extracting and analyzing skills from text like resumes and job descriptions.

### Quick Start

```python
from models.skills import SkillExtractor, SkillAnalyzer

# Extract skills from text
extractor = SkillExtractor()
skills = extractor.extract_skills("Experienced Python developer with Django and React experience")

# Analyze a resume
analyzer = SkillAnalyzer()
analysis = analyzer.analyze_resume(resume_text)

# Analyze a job description
job_analysis = analyzer.analyze_job(job_description)

# Compare resume to job description (gap analysis)
gap_analysis = analyzer.skill_gap_analysis(resume_text, job_description)

# Get skill recommendations based on resume
recommendations = analyzer.recommend_skills(resume_text)
```

### Testing

You can test the skill extraction functionality using the provided test script:

```bash
# Run with sample data
python models/skills/test_skills.py

# Run with verbose output
python models/skills/test_skills.py --verbose

# Test with specific files
python models/skills/test_skills.py --resume path/to/resume.txt --job path/to/job.txt

# Test with direct text input
python models/skills/test_skills.py --text "Python developer with 5 years experience"
```

## Dependencies

- Python 3.12+
- spaCy (optional, enables better NLP-based extraction)
- pandas (optional, enables better data analysis)

To install spaCy and its English language model:

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

## Additional Information

The skill extraction works in three modes:

1. **Direct Matching**: Matches exactly against a list of known skills
2. **Pattern-Based Extraction**: Uses regex patterns to identify common skills, doesn't require spaCy
3. **NLP-Based Extraction**: Uses spaCy for more advanced NLP-based extraction when available 