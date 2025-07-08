import os
from typing import List, Dict, Any
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

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
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates educational study cards with informative content. Focus on clear, concise explanations rather than questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
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

def generate_quiz_questions(chunks: List[Dict[str, Any]], num_questions: int = 5) -> List[Dict[str, Any]]:
    """Generate quiz questions using OpenAI's GPT model."""
    try:
        # Combine chunks into a single context
        context = "\n".join([chunk['content'] for chunk in chunks])
        
        # Create the prompt for multiple choice questions only
        prompt = f"""Based on the following content, generate {num_questions} multiple-choice quiz questions.
        Each question should have:
        1. A clear question
        2. Exactly four possible answers (A, B, C, D)
        3. Only one correct answer
        4. A helpful hint
        
        Content:
        {context}
        
        Format each question as:
        Q: [Question]
        A) [Option A]
        B) [Option B]
        C) [Option C]
        D) [Option D]
        Correct: [Letter of correct answer]
        Hint: [Helpful hint]
        
        Generate exactly {num_questions} multiple-choice questions:"""
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates educational multiple-choice quiz questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        # Parse the response
        questions_text = response.choices[0].message.content
        questions = []
        
        # Split the response into individual questions
        current_question = {}
        options = []
        
        for line in questions_text.split('\n'):
            if line.startswith('Q:'):
                if current_question:
                    current_question['options'] = options
                    questions.append(current_question)
                current_question = {'question': line[2:].strip()}
                options = []
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                options.append(line[2:].strip())
            elif line.startswith('Correct:'):
                current_question['correct_answer'] = line[8:].strip()
            elif line.startswith('Hint:'):
                current_question['hint'] = line[5:].strip()
        
        if current_question:
            current_question['options'] = options
            questions.append(current_question)
        
        return questions[:num_questions]
        
    except Exception as e:
        raise Exception(f"Error generating quiz questions: {str(e)}")

def answer_question(question: str, chunks: List[Dict[str, Any]]) -> str:
    """Answer a question using OpenAI's GPT model and relevant content chunks."""
    try:
        # Combine relevant chunks into context
        context = "\n".join([chunk['content'] for chunk in chunks])
        
        # Create the prompt
        prompt = f"""Answer the following question based on the provided content.
        If the answer cannot be found in the content, say so.
        Provide a clear and concise answer.
        
        Content:
        {context}
        
        Question: {question}"""
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on provided content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        raise Exception(f"Error answering question: {str(e)}") 