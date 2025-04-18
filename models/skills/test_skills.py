#!/usr/bin/env python
"""
Test script for the skill extractor and analyzer.
Run this script to see how the skill extraction works in practice.
"""

import json
import argparse
from .skill_extractor import SkillExtractor
from .skill_analyzer import SkillAnalyzer

def test_extraction(text, verbose=False, min_confidence=0.0):
    """Test the skill extractor on a sample text."""
    print("\n===== SKILL EXTRACTION TEST =====")
    extractor = SkillExtractor()
    
    print(f"Input text: {text[:100]}..." if len(text) > 100 else f"Input text: {text}")
    
    skills = extractor.extract_skills(text)
    
    # Filter by confidence if specified
    if min_confidence > 0:
        filtered_skills = [s for s in skills if s['confidence'] >= min_confidence]
        print(f"\nExtracted {len(filtered_skills)} high-confidence skills (confidence >= {min_confidence}):")
        print(f"(Filtered out {len(skills) - len(filtered_skills)} lower confidence skills)")
        skills_to_display = filtered_skills
    else:
        print(f"\nExtracted {len(skills)} skills:")
        skills_to_display = skills
    
    for skill in skills_to_display:
        print(f"- {skill['skill']} (Confidence: {skill['confidence']:.2f}, Method: {skill['extraction_method']})")
        
        if verbose:
            print(f"  Start: {skill['start_pos']}, End: {skill['end_pos']}")
            if 'category' in skill:
                print(f"  Category: {skill['category']}")
    
    return skills

def test_resume_analysis(resume_text, min_confidence=0.7):
    """Test resume skill analysis."""
    print("\n===== RESUME ANALYSIS TEST =====")
    analyzer = SkillAnalyzer(min_confidence=min_confidence)
    
    analysis = analyzer.analyze_resume(resume_text)
    
    print(f"\nTotal high-confidence skills found: {analysis['skill_count']} (confidence >= {min_confidence})")
    print(f"Total skills extracted: {analysis['total_extracted']}")
    print(f"Filtered out: {analysis['filtered_out']} lower confidence skills")
    
    print("\nTop skills:")
    for skill in analysis['top_skills']:
        print(f"- {skill['skill']} (Confidence: {skill['confidence']:.2f})")
    
    print("\nSkill scores by category:")
    for category, score in analysis['skill_scores'].items():
        print(f"- {category}: {score:.1f}%")
    
    return analysis

def test_job_analysis(job_text, min_confidence=0.7):
    """Test job description skill analysis."""
    print("\n===== JOB ANALYSIS TEST =====")
    analyzer = SkillAnalyzer(min_confidence=min_confidence)
    
    analysis = analyzer.analyze_job(job_text)
    
    print(f"\nTotal high-confidence skills found: {analysis['skill_count']} (confidence >= {min_confidence})")
    print(f"Total skills extracted: {analysis['total_extracted']}")
    print(f"Filtered out: {analysis['filtered_out']} lower confidence skills")
    
    print("\nRequired skills (confidence >= 0.85):")
    for skill in analysis['required_skills']:
        print(f"- {skill['skill']} (Confidence: {skill['confidence']:.2f})")
    
    print("\nPreferred skills (confidence >= 0.7):")
    for skill in analysis['preferred_skills']:
        print(f"- {skill['skill']} (Confidence: {skill['confidence']:.2f})")
    
    return analysis

def test_skill_gap(resume_text, job_text, min_confidence=0.7):
    """Test skill gap analysis between resume and job."""
    print("\n===== SKILL GAP ANALYSIS TEST =====")
    analyzer = SkillAnalyzer(min_confidence=min_confidence)
    
    gap_analysis = analyzer.skill_gap_analysis(resume_text, job_text)
    
    print(f"\nMatch Score: {gap_analysis['match_score']:.1f}%")
    print(f"Explanation: {gap_analysis['match_explanation']}")
    print("\nWhat the match score means:")
    print("- 90-100%: Excellent match - your skills align very well with the job requirements")
    print("- 75-89%: Strong match - you have most key skills required for this position")
    print("- 50-74%: Moderate match - you have many relevant skills but are missing some key requirements")
    print("- 25-49%: Below average match - you need to develop several key skills for this role")
    print("- 0-24%: Low match - this position requires many skills not found in your profile")
    
    print("\nMatching Skills:")
    for skill in gap_analysis['matching_skills']:
        print(f"- {skill['skill']}")
    
    print("\nCritical Missing Skills (required by job):")
    for skill in gap_analysis['critical_missing_skills']:
        print(f"- {skill['skill']}")
    
    # Get recommendations
    recommendations = analyzer.recommend_skills(resume_text)
    
    print("\nSkill Recommendations:")
    for rec in recommendations:
        print(f"- {rec['skill']}: {rec['reason']}")
    
    return gap_analysis

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description='Test skill extraction and analysis')
    parser.add_argument('--resume', type=str, help='Path to a resume text file')
    parser.add_argument('--job', type=str, help='Path to a job description text file')
    parser.add_argument('--text', type=str, help='Text to analyze directly')
    parser.add_argument('--verbose', action='store_true', help='Show verbose output')
    parser.add_argument('--min-confidence', type=float, default=0.7, 
                        help='Minimum confidence threshold (0.0-1.0, default: 0.7)')
    parser.add_argument('--all', action='store_true', 
                        help='Show all skills including low confidence ones')
    
    args = parser.parse_args()
    min_confidence = 0.0 if args.all else args.min_confidence
    
    # Sample texts if no files provided
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
    
    if args.text:
        # Simple extraction test on provided text
        test_extraction(args.text, args.verbose, min_confidence)
    elif args.resume or args.job:
        # Load text from files if provided
        resume_text = sample_resume
        job_text = sample_job
        
        if args.resume:
            with open(args.resume, 'r') as f:
                resume_text = f.read()
        
        if args.job:
            with open(args.job, 'r') as f:
                job_text = f.read()
        
        # Run all tests
        if args.resume:
            test_extraction(resume_text, args.verbose, min_confidence)
            test_resume_analysis(resume_text, min_confidence)
        
        if args.job:
            test_extraction(job_text, args.verbose, min_confidence)
            test_job_analysis(job_text, min_confidence)
        
        if args.resume and args.job:
            test_skill_gap(resume_text, job_text, min_confidence)
    else:
        # Use sample texts for demonstration
        print("Using sample texts for demonstration...")
        test_extraction(sample_resume, args.verbose, min_confidence)
        test_resume_analysis(sample_resume, min_confidence)
        test_job_analysis(sample_job, min_confidence)
        test_skill_gap(sample_resume, sample_job, min_confidence)

if __name__ == "__main__":
    main() 