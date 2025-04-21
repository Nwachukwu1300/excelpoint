import requests
import json

def extract_skills_api(text, min_confidence=0.7, api_url=None):
    """
    Extract skills from text using the Career Nexus API.
    
    Args:
        text: The text to analyze
        min_confidence: Minimum confidence threshold (0.0-1.0)
        api_url: URL to the API endpoint (default: localhost)
        
    Returns:
        Dictionary containing extracted skills if successful
    """
    if api_url is None:
        api_url = "http://localhost:8000/skills/models/api/basic-extract-skills/"
    
    # Prepare the request payload
    payload = {
        "text": text,
        "min_confidence": min_confidence
    }
    
    # Set headers for JSON content
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # Make the POST request
        response = requests.post(api_url, data=json.dumps(payload), headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            return data
        else:
            print(f"Error: API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred during API request: {str(e)}")
        return None

def display_results(results):
    """Display skill extraction results in a readable format."""
    if not results or not results.get('success', False):
        print("No valid results to display.")
        return
    
    print("\n===== SKILL EXTRACTION RESULTS =====")
    print(f"Total skills found: {results['skills_count']}")
    print(f"spaCy available: {'Yes' if results.get('spacy_available', False) else 'No'}")
    
    print("\nSkills by Category:")
    for category, skills in results.get('skills_by_category', {}).items():
        print(f"\n{category.title()}:")
        for skill in skills:
            print(f"  - {skill}")
    
    print("\nDetailed Skills:")
    for skill in results.get('skills', []):
        print(f"  - {skill['skill']} (Confidence: {skill['confidence']:.2f}, Method: {skill.get('extraction_method', 'unknown')})")


if __name__ == "__main__":
    # Sample job description
    sample_text = """
    Senior Software Engineer
    
    Requirements:
    - 5+ years of experience with Python and Django
    - Strong knowledge of JavaScript and React
    - Experience with AWS, Docker, and CI/CD pipelines
    - Good understanding of database design and SQL
    - Excellent communication and problem-solving skills
    
    Nice to have:
    - Experience with TypeScript and Redux
    - Knowledge of GraphQL and RESTful API design
    - Agile development methodology experience
    """
    
    print("Analyzing sample job description...")
    results = extract_skills_api(sample_text)
    
    if results:
        display_results(results)
    
    # Example of saving extracted skills to file
    if results and results.get('success', False):
        output_file = "extracted_skills.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_file}")
    
    print("\nTo use this script with your own text:")
    print("1. Make sure the Career Nexus server is running")
    print("2. Modify the sample_text variable or create a new function to read from a file")
    print("3. Run the script with: python sample_skill_extractor_usage.py") 