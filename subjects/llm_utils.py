from typing import List, Dict, Any
from openai import OpenAI
from django.conf import settings

# Remove the global client initialization - we'll create it dynamically in each function

def generate_flashcards(chunks: List[Dict[str, Any]], num_cards: int = 5) -> List[Dict[str, str]]:
    """Generate informational flashcards using OpenAI's GPT model."""
    try:
        # Combine chunks into a single context
        context = "\n".join([chunk['content'] for chunk in chunks])
        
        # Create the prompt for informational flashcards
        prompt = f"""Based on the following content, create {num_cards} informational study cards.
        Each card should:
        1. Have a clear, descriptive title/topic
        2. Contain exactly 2 sentences of key information about that topic
        3. Focus on important concepts, definitions, or facts
        4. Be educational and informative rather than question-based
        
        Content:
        {context}
        
        Format each flashcard as:
        TOPIC: [Descriptive title/concept name]
        INFO: [First sentence with key information. Second sentence with additional important details.]
        
        Generate exactly {num_cards} informational study cards:"""
        
        # Create client dynamically to ensure fresh settings
        dynamic_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Call OpenAI API
        response = dynamic_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates educational study cards with informative content. Focus on clear, concise explanations rather than questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_completion_tokens=1000
        )
        
        # Parse the response
        flashcards_text = response.choices[0].message.content
        flashcards = []
        
        # Split the response into individual flashcards
        current_card = {}
        for line in flashcards_text.split('\n'):
            line = line.strip()
            if line.startswith('TOPIC:'):
                if current_card:
                    flashcards.append(current_card)
                current_card = {'question': line[6:].strip()}  # Keep 'question' field for compatibility
            elif line.startswith('INFO:'):
                current_card['answer'] = line[5:].strip()     # Keep 'answer' field for compatibility
        
        if current_card and 'question' in current_card and 'answer' in current_card:
            flashcards.append(current_card)
        
        return flashcards[:num_cards]
        
    except Exception as e:
        raise Exception(f"Error generating flashcards: {str(e)}")
