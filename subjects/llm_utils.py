from typing import List, Dict, Any
from openai import OpenAI
from django.conf import settings

# Remove the global client initialization - we'll create it dynamically in each function

def generate_flashcards(chunks: List[Dict[str, Any]], num_cards: int = 5) -> List[Dict[str, str]]:
    """Generate informational flashcards using OpenAI's GPT model."""
    try:
        # Combine chunks into a single context
        context = "\n".join([chunk['content'] for chunk in chunks])
        
        # The front must be a question: a title alone ("Photosynthesis Overview") doesn't say what to recall
        prompt = f"""Based on the following content, create {num_cards} flashcards for spaced-repetition review.
        Each card should:
        1. Ask one clear question about an important concept, definition or fact in the content
        2. Give the answer in 1 or 2 short sentences, using only the content
        3. Use plain words a student can answer from memory

        Content:
        {context}

        Format each flashcard as:
        QUESTION: [A question, ending with a question mark]
        ANSWER: [The answer in 1 or 2 sentences]

        Generate exactly {num_cards} flashcards:"""
        
        # Create client dynamically to ensure fresh settings
        dynamic_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Call OpenAI API
        response = dynamic_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You write clear study flashcards: a question on the front, a short answer on the back."},
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
            label, _, text = line.partition(':')
            if label in ('QUESTION', 'TOPIC'):  # TOPIC/INFO: the old card format
                if current_card:
                    flashcards.append(current_card)
                current_card = {'question': text.strip()}
            elif label in ('ANSWER', 'INFO') and current_card:
                current_card['answer'] = text.strip()
        
        if current_card and 'question' in current_card and 'answer' in current_card:
            flashcards.append(current_card)
        
        return flashcards[:num_cards]
        
    except Exception as e:
        raise Exception(f"Error generating flashcards: {str(e)}")
