# CareerNexus - Career Development Platform

## Project Overview
CareerNexus is a comprehensive career development platform that helps users manage their professional growth through skill assessment, job matching, and personalized learning recommendations.

## Current Implementation Status

### Completed Features
- **User Authentication System**
 - Registration with email validation
 - Login/Logout functionality
 - Profile management
 - Password change capabilities
 - Session-based authentication
- **Skill Extraction and Analysis**
 - Pattern-based skill extraction (no dependencies required)
 - Optional NLP-based skill extraction (requires spaCy)
 - Skill gap analysis against job roles
 - Course recommendations based on missing skills
 - API endpoints for skill extraction

### Pending Features
- **API Integrations**
 - Job search (LinkedIn, Glassdoor)
 - Learning platforms (Coursera, Udemy)
 - Portfolio integration
 - Trend analysis
- **Core Functionality**
 - Skill assessment
 - Job matching
 - Course recommendations
 - Market trend analysis

## Technical Stack
- **Backend**: Django/Python
- **Database**: PostgreSQL
- **Authentication**: Session-based
- **API Framework**: Django REST Framework

## Skill Extraction API

CareerNexus provides a flexible skill extraction system with two operational modes:

1. **Basic Mode**: Pattern-based extraction that works without additional dependencies
2. **Advanced Mode**: NLP-powered extraction that requires spaCy

### Using the Skill Extraction API

#### Web Interface
- Access the basic skill extraction form at: `/skills/models/api/basic-extract-skills/`
- This interface allows you to extract skills from text without requiring spaCy

#### Programmatic API
```python
import requests
import json

# Example API call
response = requests.post(
    "http://localhost:8000/skills/models/api/basic-extract-skills/",
    headers={"Content-Type": "application/json"},
    data=json.dumps({
        "text": "Your job description or resume text",
        "min_confidence": 0.7
    })
)

# Process results
if response.status_code == 200:
    skills_data = response.json()
    print(f"Found {skills_data['skills_count']} skills")
```

See `skills/sample_skill_extractor_usage.py` for a complete example.

