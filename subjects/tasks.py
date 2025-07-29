# Force CPU usage and prevent MPS crashes on macOS - MUST BE FIRST!
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'

# Force PyTorch to use CPU before any ML libraries are imported
try:
    import torch
    torch.set_default_device('cpu')
    # Disable MPS backend completely
    if hasattr(torch.backends, 'mps'):
        torch.backends.mps.is_available = lambda: False
except ImportError:
    pass

from celery import shared_task
from .models import SubjectMaterial, ContentChunk, Flashcard, QuizQuestion, Quiz, Question, Choice, Answer, UserQuizAttempt
from .utils import ContentProcessor
from openai import OpenAI
import logging
import json
import re
from django.conf import settings
from .utils import extract_text_from_pdf, chunk_text
from django.utils import timezone
from django.db import models

logger = logging.getLogger(__name__)

# Remove global client initialization - we'll create it dynamically in each function

@shared_task
def process_material(material_id: int):
    """Process uploaded material and create chunks with enhanced embedding status tracking."""
    try:
        material = SubjectMaterial.objects.get(id=material_id)
        material.status = 'PROCESSING'
        material.save()
        
        # Initialize ContentProcessor with batch processing for large files
        processor = ContentProcessor(memory_threshold=0.7)  # Use batch processing if memory > 70%
        file_path = material.file.path
        
        # Process the file using the unified processor with automatic batch processing
        chunks_data = processor.process_file(file_path)
        
        # Create ContentChunk objects with embedding status tracking
        for chunk_data in chunks_data:
            chunk = ContentChunk.objects.create(
                material=material,
                content=chunk_data['content'],
                chunk_index=chunk_data['chunk_index'],
                embedding_vector=chunk_data['embedding_vector'],
                embedding_status='completed'  # Mark as completed since we just generated it
            )
            logger.debug(f"Created chunk {chunk.chunk_index} with embedding for material {material.file.name}")
        
        # Update material status to completed before queuing additional tasks
        material.status = 'COMPLETED'
        material.save()
        
        logger.info(f"Successfully processed material {material.file.name} with {len(chunks_data)} chunks")
        
        # Queue additional tasks only after material is successfully processed
        # Use apply_async with countdown to ensure material is fully saved
        generate_flashcards.apply_async(args=[material_id], countdown=2)
        generate_quiz_from_material.apply_async(args=[material_id, 10], countdown=2)  # Use new quiz system with 10 questions
        
    except Exception as e:
        logger.exception(f"Error processing material {material_id}: {str(e)}")
        try:
            material = SubjectMaterial.objects.get(id=material_id)
            material.status = 'FAILED'
            material.save()
        except:
            pass
        raise e

@shared_task
def generate_flashcards(material_id: int):
    """Generate flashcards from processed material."""
    try:
        # Add more detailed logging for debugging
        logger.info(f"Starting flashcard generation for material ID: {material_id}")
        
        # Check if material exists before proceeding
        try:
            material = SubjectMaterial.objects.get(id=material_id)
        except SubjectMaterial.DoesNotExist:
            logger.error(f"Material with ID {material_id} does not exist in database")
            return {'status': 'error', 'message': f'Material with ID {material_id} not found'}
        
        logger.info(f"Generating flashcards for material ID {material_id}: {material.file.name}")
        
        # Check if material is in completed status
        if material.status != 'COMPLETED':
            logger.warning(f"Material {material_id} is not in COMPLETED status (current: {material.status})")
            return {'status': 'error', 'message': f'Material {material_id} is not ready for processing (status: {material.status})'}
        
        chunks = ContentChunk.objects.filter(material=material)
        logger.info(f"Found {chunks.count()} content chunks for material {material_id}")
        
        if chunks.count() == 0:
            logger.warning(f"No content chunks found for material {material_id}")
            return {'status': 'error', 'message': f'No content chunks found for material {material_id}'}
        
        processor = ContentProcessor()
        chunks_data = [
            {
                'content': chunk.content,
                'chunk_index': chunk.chunk_index,
                'embedding_vector': chunk.embedding_vector
            }
            for chunk in chunks
        ]
        
        flashcards = processor.generate_flashcards(chunks_data)
        
        # Create Flashcard objects
        flashcard_count = 0
        for flashcard in flashcards:
            Flashcard.objects.create(
                subject=material.subject,
                material=material,  # Link to specific material
                question=flashcard['question'],
                answer=flashcard['answer']
            )
            flashcard_count += 1
        
        logger.info(f"Successfully created {flashcard_count} flashcards for material {material_id}: {material.file.name}")
        return {'status': 'success', 'flashcards_created': flashcard_count}
            
    except Exception as e:
        logger.error(f"Error generating flashcards for material {material_id}: {str(e)}")
        logger.exception("Full traceback:")
        return {'status': 'error', 'message': str(e)}

@shared_task
def generate_quiz_questions(material_id: int):
    """Generate quiz questions from processed material."""
    try:
        # Add more detailed logging for debugging
        logger.info(f"Starting quiz questions generation for material ID: {material_id}")
        
        # Check if material exists before proceeding
        try:
            material = SubjectMaterial.objects.get(id=material_id)
        except SubjectMaterial.DoesNotExist:
            logger.error(f"Material with ID {material_id} does not exist in database")
            return {'status': 'error', 'message': f'Material with ID {material_id} not found'}
        
        logger.info(f"Generating quiz questions for material ID {material_id}: {material.file.name}")
        
        # Check if material is in completed status
        if material.status != 'COMPLETED':
            logger.warning(f"Material {material_id} is not in COMPLETED status (current: {material.status})")
            return {'status': 'error', 'message': f'Material {material_id} is not ready for processing (status: {material.status})'}
        
        chunks = ContentChunk.objects.filter(material=material)
        logger.info(f"Found {chunks.count()} content chunks for material {material_id}")
        
        if chunks.count() == 0:
            logger.warning(f"No content chunks found for material {material_id}")
            return {'status': 'error', 'message': f'No content chunks found for material {material_id}'}
        
        processor = ContentProcessor()
        chunks_data = [
            {
                'content': chunk.content,
                'chunk_index': chunk.chunk_index,
                'embedding_vector': chunk.embedding_vector
            }
            for chunk in chunks
        ]
        
        questions = processor.generate_quiz_questions(chunks_data)
        
        # Create QuizQuestion objects
        question_count = 0
        for question in questions:
            QuizQuestion.objects.create(
                subject=material.subject,
                material=material,  # Link to specific material
                question=question['question'],
                correct_answer=question['correct_answer'],
                options=question['options'],
                hint=question['hint']
            )
            question_count += 1
        
        logger.info(f"Successfully created {question_count} quiz questions for material {material_id}: {material.file.name}")
        return {'status': 'success', 'questions_created': question_count}
            
    except Exception as e:
        logger.error(f"Error generating quiz questions for material {material_id}: {str(e)}")
        logger.exception("Full traceback:")
        return {'status': 'error', 'message': str(e)}

@shared_task(bind=True, max_retries=3, time_limit=300)  # 5 minute timeout
def generate_quiz_from_material(self, material_id, num_questions=10):
    """
    Generate a quiz with mixed question types from uploaded material content
    """
    try:
        material = SubjectMaterial.objects.get(id=material_id)
        logger.info(f"Starting quiz generation for material: {material.file.name}")
        
        # Don't change material status - it should already be COMPLETED from process_material
        
        # Extract text content
        if material.file_type == 'PDF':
            text_content = extract_text_from_pdf(material.file.path)
        elif material.file_type in ['DOCX', 'DOC']:
            # Use ContentProcessor for Word documents
            processor = ContentProcessor()
            chunks_data = processor.process_file(material.file.path)
            text_content = '\n'.join([chunk['content'] for chunk in chunks_data])
        elif material.file_type in ['VIDEO', 'AUDIO']:
            # Use ContentProcessor for video/audio files (handles transcription)
            processor = ContentProcessor()
            chunks_data = processor.process_file(material.file.path)
            text_content = '\n'.join([chunk['content'] for chunk in chunks_data])
        else:
            # For other file types, read as text
            with open(material.file.path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        
        if not text_content.strip():
            logger.warning(f"No text content found in material {material_id}")
            return {'status': 'error', 'message': 'No text content found in the uploaded file'}
        
        logger.info(f"Extracted {len(text_content)} characters from material {material_id}")
        
        # Create or get quiz for this material
        quiz, created = Quiz.objects.get_or_create(
            subject=material.subject,
            title=f"Quiz: {material.file.name}",
            defaults={
                'description': f"Auto-generated quiz from {material.file.name}",
                'pass_score': 70.0,
                'time_limit': 30  # 30 minutes default
            }
        )
        
        # Clear existing questions if regenerating
        if not created:
            quiz.questions.all().delete()
        
        # Generate questions using OpenAI with timeout
        logger.info(f"Generating {num_questions} questions for material {material_id}")
        questions_data = _generate_questions_with_openai(text_content, num_questions)
        
        if not questions_data:
            logger.warning(f"No questions generated for material {material_id}")
            return {'status': 'error', 'message': 'Failed to generate questions'}
        
        # Save questions to database
        question_order = 1
        for q_data in questions_data:
            question = Question.objects.create(
                quiz=quiz,
                text=q_data['question'],
                question_type='multiple_choice',  # Force all questions to be multiple choice
                points=q_data.get('points', 1),
                order=question_order,
                explanation=q_data.get('explanation', '')
            )
            
            # Create choices for multiple choice questions
            for i, choice_data in enumerate(q_data['options']):
                Choice.objects.create(
                    question=question,
                    text=choice_data['text'],
                    is_correct=choice_data['is_correct'],
                    order=i + 1
                )
            
            question_order += 1
        
        # Don't change material status - keep it as is
        
        logger.info(f"Successfully generated {len(questions_data)} questions for material: {material.file.name}")
        return {
            'status': 'success',
            'quiz_id': quiz.id,
            'questions_generated': len(questions_data)
        }
        
    except SubjectMaterial.DoesNotExist:
        logger.error(f"Material with id {material_id} not found")
        return {'status': 'error', 'message': 'Material not found'}
    
    except Exception as e:
        logger.exception(f"Error generating quiz for material {material_id}: {str(e)}")
        
        # Don't change material status on error - let it remain as is
        return {'status': 'error', 'message': str(e)}

def _generate_questions_with_openai(text_content, num_questions=10):
    """
    Use OpenAI to generate quiz questions from text content
    """
    try:
        # Chunk the text if it's too long
        chunks = chunk_text(text_content, chunk_size=2000)
        logger.info(f"Split text into {len(chunks)} chunks for question generation")
        
        all_questions = []
        questions_per_chunk = max(2, num_questions // len(chunks))
        
        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"Generating questions for chunk {i + 1}/{len(chunks)}")
                
                # Generate only multiple choice questions
                chunk_questions = []
                
                # Generate multiple choice questions only
                mc_prompt = _create_multiple_choice_prompt(chunk, questions_per_chunk)
                mc_response = _call_openai_api(mc_prompt)
                chunk_questions.extend(_parse_multiple_choice_response(mc_response))
                
                logger.info(f"Generated {len(chunk_questions)} questions from chunk {i + 1}")
                all_questions.extend(chunk_questions)
                
            except Exception as e:
                logger.warning(f"Error generating questions for chunk {i + 1}: {str(e)}")
                continue
        
        # Limit to requested number of questions
        final_questions = all_questions[:num_questions]
        logger.info(f"Generated {len(final_questions)} total questions (requested: {num_questions})")
        return final_questions
        
    except Exception as e:
        logger.error(f"Error in _generate_questions_with_openai: {str(e)}")
        return []

def _create_multiple_choice_prompt(text, num_questions):
    """Create prompt for multiple choice questions"""
    return f"""
Based on the following text, generate {num_questions} multiple-choice questions that test understanding of key concepts.

Text:
{text}

Instructions:
1. Create {num_questions} multiple-choice questions
2. Each question should have 4 options (A, B, C, D)
3. Only one option should be correct
4. Vary difficulty levels from basic recall to analysis
5. Questions should cover important concepts from the text

Output format (JSON):
{{
    "questions": [
        {{
            "question": "Question text here?",
            "options": [
                {{"text": "Option A", "is_correct": false}},
                {{"text": "Option B", "is_correct": true}},
                {{"text": "Option C", "is_correct": false}},
                {{"text": "Option D", "is_correct": false}}
            ],
            "explanation": "Brief explanation of why the answer is correct"
        }}
    ]
}}
"""

def _create_true_false_prompt(text, num_questions):
    """Create prompt for true/false questions"""
    return f"""
Based on the following text, generate {num_questions} true/false questions that test understanding.

Text:
{text}

Instructions:
1. Create {num_questions} true/false questions
2. Include a mix of true and false statements
3. Focus on important facts and concepts from the text
4. Avoid ambiguous statements

Output format (JSON):
{{
    "questions": [
        {{
            "question": "Statement to evaluate",
            "options": [
                {{"text": "True", "is_correct": true}},
                {{"text": "False", "is_correct": false}}
            ],
            "explanation": "Brief explanation of why the statement is true or false"
        }}
    ]
}}
"""

def _create_short_answer_prompt(text, num_questions):
    """Create prompt for short answer questions"""
    return f"""
Based on the following text, generate {num_questions} short answer questions that require brief responses.

Text:
{text}

Instructions:
1. Create {num_questions} short answer questions
2. Questions should require 1-3 sentence responses
3. Focus on key concepts, definitions, and explanations
4. Provide model answers and acceptable variations

Output format (JSON):
{{
    "questions": [
        {{
            "question": "Question text here?",
            "correct_answers": ["Primary answer", "Alternative answer", "Another acceptable answer"],
            "explanation": "Brief explanation of what makes a good answer"
        }}
    ]
}}
"""

def _call_openai_api(prompt, temperature=0.3, max_retries=3):
    """
    Call OpenAI API with error handling and retries
    """
    import time
    
    for attempt in range(max_retries):
        try:
            # Create client dynamically to ensure fresh settings
            from django.conf import settings
            dynamic_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = dynamic_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a quiz generation assistant. Generate high-quality educational questions based on the provided text. Always respond with valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=2000,
                timeout=30  # 30 second timeout
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            # Handle rate limiting with exponential backoff
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 20 * (2 ** attempt)  # Exponential backoff: 20s, 40s, 80s
                logger.warning(f"OpenAI rate limit reached, waiting {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            
            logger.error(f"OpenAI API error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)  # Short delay before retry

def _parse_multiple_choice_response(response):
    """Parse OpenAI response for multiple choice questions"""
    try:
        data = json.loads(response)
        questions = []
        
        for q in data.get('questions', []):
            questions.append({
                'type': 'multiple_choice',
                'question': q['question'],
                'options': q['options'],
                'explanation': q.get('explanation', ''),
                'points': 1
            })
        
        return questions
    
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Error parsing multiple choice response: {str(e)}")
        return []

def _parse_true_false_response(response):
    """Parse OpenAI response for true/false questions"""
    try:
        data = json.loads(response)
        questions = []
        
        for q in data.get('questions', []):
            questions.append({
                'type': 'true_false',
                'question': q['question'],
                'options': q['options'],
                'explanation': q.get('explanation', ''),
                'points': 1
            })
        
        return questions
    
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Error parsing true/false response: {str(e)}")
        return []

def _parse_short_answer_response(response):
    """Parse OpenAI response for short answer questions"""
    try:
        data = json.loads(response)
        questions = []
        
        for q in data.get('questions', []):
            questions.append({
                'type': 'short_answer',
                'question': q['question'],
                'correct_answers': q['correct_answers'],
                'explanation': q.get('explanation', ''),
                'points': 2  # Short answer questions worth more points
            })
        
        return questions
    
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Error parsing short answer response: {str(e)}")
        return []

@shared_task(bind=True)
def generate_dynamic_quiz_questions(self, attempt_id, num_questions=10):
    """
    Generate dynamic questions for a specific quiz attempt.
    This creates unique questions for each attempt rather than using static questions.
    """
    try:
        attempt = UserQuizAttempt.objects.get(id=attempt_id)
        quiz = attempt.quiz
        material = quiz.subject.materials.first()  # Get the first material for now
        
        if not material:
            raise ValueError("No material found for this quiz")
        
        logger.info(f"Generating dynamic questions for attempt {attempt_id}")
        
        # Get text content from processed content chunks instead of raw file
        content_chunks = ContentChunk.objects.filter(material=material)
        
        if not content_chunks.exists():
            logger.warning(f"No content chunks found for material {material.id}, falling back to file processing")
            # Fallback: Extract text content from the material file
            if material.file_type == 'PDF':
                text_content = extract_text_from_pdf(material.file.path)
            elif material.file_type in ['DOCX', 'DOC']:
                # Use ContentProcessor for Word documents
                processor = ContentProcessor()
                chunks_data = processor.process_file(material.file.path)
                text_content = '\n'.join([chunk['content'] for chunk in chunks_data])
            elif material.file_type in ['VIDEO', 'AUDIO']:
                # Use ContentProcessor for video/audio files (handles transcription)
                processor = ContentProcessor()
                chunks_data = processor.process_file(material.file.path)
                text_content = '\n'.join([chunk['content'] for chunk in chunks_data])
            else:
                # For other file types, try to read as text
                try:
                    with open(material.file.path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                except UnicodeDecodeError:
                    logger.error(f"Cannot read file {material.file.name} as text")
                    return {'status': 'error', 'message': 'Cannot read file as text'}
        else:
            # Use processed content chunks
            logger.info(f"Using {content_chunks.count()} processed content chunks for material {material.id}")
            text_content = '\n'.join([chunk.content for chunk in content_chunks])
        
        if not text_content.strip():
            logger.warning(f"No text content found for material {material.id}")
            return {'status': 'error', 'message': 'No text content found in the material'}
        
        logger.info(f"Extracted {len(text_content)} characters for dynamic question generation")
        
        # Generate dynamic questions with variation
        questions_data = _generate_dynamic_questions_with_openai(
            text_content, 
            num_questions, 
            attempt_number=attempt.user.quiz_attempts.filter(quiz=quiz).count()
        )
        
        if not questions_data:
            logger.warning(f"No dynamic questions generated for attempt {attempt_id}")
            return {'status': 'error', 'message': 'Failed to generate dynamic questions'}
        
        # Store the generated questions directly in the attempt as JSON
        formatted_questions = []
        for i, q_data in enumerate(questions_data):
            formatted_question = {
                'id': f"dynamic_{i+1}",
                'text': q_data['question'],
                'type': q_data['type'],
                'points': q_data.get('points', 1),
                'explanation': q_data.get('explanation', ''),
                'order': i + 1
            }
            
            # Add choices for multiple choice and true/false
            if q_data['type'] in ['multiple_choice', 'true_false']:
                formatted_question['choices'] = []
                for j, choice_data in enumerate(q_data['options']):
                    formatted_question['choices'].append({
                        'id': f"dynamic_{i+1}_choice_{j+1}",
                        'text': choice_data['text'],
                        'is_correct': choice_data['is_correct'],
                        'order': j + 1
                    })
            
            # Add correct answers for short answer
            elif q_data['type'] == 'short_answer':
                formatted_question['correct_answers'] = q_data.get('correct_answers', [])
            
            formatted_questions.append(formatted_question)
        
        # Store questions in the attempt
        attempt.dynamic_questions = formatted_questions
        attempt.uses_dynamic_questions = True  # Mark this attempt as using dynamic questions
        attempt.save()
        
        logger.info(f"Successfully generated {len(questions_data)} dynamic questions for attempt {attempt_id}")
        return {
            'status': 'success',
            'attempt_id': attempt_id,
            'questions_generated': len(questions_data)
        }
        
    except UserQuizAttempt.DoesNotExist:
        logger.error(f"Quiz attempt with id {attempt_id} not found")
        return {'status': 'error', 'message': 'Quiz attempt not found'}
    
    except Exception as e:
        logger.exception(f"Error generating dynamic questions for attempt {attempt_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def _generate_dynamic_questions_with_openai(text_content, num_questions=10, attempt_number=1):
    """
    Generate dynamic questions with variation based on attempt number
    """
    # Add variation to the prompt based on attempt number
    variation_instructions = {
        1: "Focus on fundamental concepts and definitions.",
        2: "Emphasize practical applications and examples.",
        3: "Create questions about relationships and comparisons between concepts.",
        4: "Focus on analysis and critical thinking questions.",
    }
    
    variation_instruction = variation_instructions.get(
        attempt_number, 
        "Create diverse questions covering different aspects of the material."
    )
    
    # Chunk the text if it's too long
    chunks = chunk_text(text_content, chunk_size=2000)
    
    all_questions = []
    questions_per_chunk = max(2, num_questions // len(chunks))
    
    for i, chunk in enumerate(chunks):
        try:
            # Generate questions with variation
            chunk_questions = []
            
            # Create a dynamic prompt that requests JSON format
            dynamic_prompt = f"""
Based on the following text, generate {questions_per_chunk} multiple-choice quiz questions in JSON format.

Variation Focus: {variation_instruction}
Attempt Number: {attempt_number}

Text:
{chunk}

Instructions:
1. Create {questions_per_chunk} multiple-choice questions ONLY
2. Each question must have exactly 4 options (A, B, C, D)
3. Only one option should be correct
4. {variation_instruction}
5. Vary difficulty and focus areas
6. Avoid repetitive patterns

Please respond with valid JSON in this exact format:
{{
    "questions": [
        {{
            "QUESTION_TYPE": "multiple_choice",
            "QUESTION": "Your question here?",
            "OPTIONS": "A) option1, B) option2, C) option3, D) option4",
            "CORRECT": "B) option2",
            "EXPLANATION": "Brief explanation of the correct answer",
            "POINTS": 1
        }}
    ]
}}

Generate exactly {questions_per_chunk} multiple-choice questions:
"""
            
            response = _call_openai_api(dynamic_prompt, temperature=0.8)  # Higher temperature for more variation
            chunk_questions.extend(_parse_dynamic_response(response))
            
            all_questions.extend(chunk_questions)
            
        except Exception as e:
            logger.warning(f"Error generating dynamic questions for chunk {i + 1}: {str(e)}")
            continue
    
    # Shuffle and limit to requested number
    import random
    random.shuffle(all_questions)
    return all_questions[:num_questions]

def _parse_dynamic_response(response):
    """Parse the dynamic question response format - handles multiple choice questions only"""
    questions = []
    
    # First try to parse as JSON
    try:
        import json
        data = json.loads(response)
        if 'questions' in data:
            for q_data in data['questions']:
                question = {
                    'type': 'multiple_choice',  # Force multiple choice
                    'question': q_data.get('QUESTION', ''),
                    'explanation': q_data.get('EXPLANATION', ''),
                    'points': q_data.get('POINTS', 1)
                }
                
                # Parse multiple choice options
                options_text = q_data.get('OPTIONS', '')
                correct_answer = q_data.get('CORRECT', '')
                
                options = []
                # Parse options like "A) option1, B) option2, C) option3, D) option4"
                for opt in options_text.split(', '):
                    opt = opt.strip()
                    if len(opt) > 3 and opt[1] == ')':
                        letter = opt[0].upper()
                        text = opt[3:].strip()
                        is_correct = correct_answer.startswith(letter)
                        options.append({'text': text, 'is_correct': is_correct})
                
                question['options'] = options
                questions.append(question)
        
        return questions
    
    except (json.JSONDecodeError, KeyError):
        # Fall back to text parsing if JSON fails
        pass
    
    # Text format parsing for multiple choice only
    lines = response.strip().split('\n')
    current_question = {}
    
    for line in lines:
        line = line.strip()
        if line.startswith('QUESTION_TYPE:'):
            if current_question:
                questions.append(current_question)
            current_question = {'type': 'multiple_choice'}  # Force multiple choice
        elif line.startswith('QUESTION:'):
            current_question['question'] = line.split(':', 1)[1].strip()
        elif line.startswith('OPTIONS:'):
            options_text = line.split(':', 1)[1].strip()
            options = []
            for opt in options_text.split(', '):
                letter = opt.strip()[0]
                text = opt.strip()[3:]
                options.append({'text': text, 'is_correct': False})
            current_question['options'] = options
        elif line.startswith('CORRECT:'):
            correct_answer = line.split(':', 1)[1].strip()
            # Mark the correct option
            if 'options' in current_question:
                correct_letter = correct_answer[0].upper()
                correct_index = ord(correct_letter) - ord('A')
                if 0 <= correct_index < len(current_question['options']):
                    current_question['options'][correct_index]['is_correct'] = True
        elif line.startswith('EXPLANATION:'):
            current_question['explanation'] = line.split(':', 1)[1].strip()
        elif line.startswith('POINTS:'):
            try:
                current_question['points'] = int(line.split(':', 1)[1].strip())
            except:
                current_question['points'] = 1
    
    if current_question:
        questions.append(current_question)
    
    return questions 


# Enhanced Embedding Generation Tasks

@shared_task(bind=True, max_retries=3)
def process_subject_embeddings(self, subject_id: int):
    """
    Process embeddings for all materials in a subject.
    Handles materials that don't have embeddings or have failed embedding generation.
    """
    try:
        from .models import Subject, SubjectMaterial, ContentChunk
        
        subject = Subject.objects.get(id=subject_id)
        logger.info(f"Starting embedding processing for subject: {subject.name} (ID: {subject_id})")
        
        # Get all materials for this subject
        materials = SubjectMaterial.objects.filter(subject=subject)
        
        processed_count = 0
        error_count = 0
        
        for material in materials:
            try:
                # Check if material has chunks that need embedding processing
                pending_chunks = ContentChunk.objects.filter(
                    material=material, 
                    embedding_status__in=['pending', 'failed']
                ).count()
                
                missing_embedding_chunks = ContentChunk.objects.filter(
                    material=material,
                    embedding_vector__isnull=True
                ).count()
                
                if pending_chunks > 0 or missing_embedding_chunks > 0:
                    logger.info(f"Processing material: {material.file.name} ({pending_chunks} pending, {missing_embedding_chunks} missing embeddings)")
                    
                    # Process material embeddings with retry logic
                    process_material_embeddings.delay(material.id)
                    processed_count += 1
                else:
                    logger.info(f"Skipping material: {material.file.name} (all embeddings completed)")
                    
            except Exception as e:
                logger.error(f"Error processing material {material.id}: {str(e)}")
                error_count += 1
                continue
        
        logger.info(f"Subject embedding processing completed: {processed_count} materials queued, {error_count} errors")
        
        return {
            'status': 'success',
            'subject_id': subject_id,
            'materials_processed': processed_count,
            'errors': error_count
        }
        
    except Subject.DoesNotExist:
        logger.error(f"Subject with id {subject_id} not found")
        return {'status': 'error', 'message': 'Subject not found'}
        
    except Exception as e:
        logger.exception(f"Error processing subject embeddings for {subject_id}: {str(e)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 60  # 1, 2, 4 minutes
            logger.info(f"Retrying subject embedding processing in {countdown} seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=countdown, exc=e)
        else:
            logger.error(f"Max retries exceeded for subject embedding processing: {subject_id}")
            return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def process_material_embeddings(self, material_id: int):
    """
    Process embeddings for all chunks in a material with retry logic.
    Only processes chunks that need embedding generation (pending/failed/missing).
    """
    try:
        from .models import SubjectMaterial, ContentChunk
        
        material = SubjectMaterial.objects.get(id=material_id)
        logger.info(f"Processing embeddings for material: {material.file.name} (ID: {material_id})")
        
        # Update material status
        material.status = 'PROCESSING'
        material.save()
        
        # Get chunks that need embedding processing
        chunks_to_process = ContentChunk.objects.filter(
            material=material,
            embedding_status__in=['pending', 'failed']
        )
        
        # Also include chunks that somehow don't have embeddings
        chunks_missing_embeddings = ContentChunk.objects.filter(
            material=material,
            embedding_vector__isnull=True
        )
        
        # Combine and deduplicate
        all_chunks_to_process = chunks_to_process.union(chunks_missing_embeddings)
        
        total_chunks = all_chunks_to_process.count()
        
        if total_chunks == 0:
            logger.info(f"No chunks need embedding processing for material: {material.file.name}")
            material.status = 'COMPLETED'
            material.save()
            return {
                'status': 'success',
                'material_id': material_id,
                'chunks_processed': 0,
                'message': 'No chunks needed processing'
            }
        
        logger.info(f"Found {total_chunks} chunks needing embedding processing")
        
        # Process chunks in smaller batches to avoid memory issues
        batch_size = 10  # Process 10 chunks at a time
        processed_count = 0
        failed_count = 0
        
        for i in range(0, total_chunks, batch_size):
            batch_chunks = all_chunks_to_process[i:i + batch_size]
            
            for chunk in batch_chunks:
                try:
                    # Generate embedding for individual chunk
                    generate_chunk_embedding.delay(chunk.id)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error queuing embedding for chunk {chunk.id}: {str(e)}")
                    chunk.mark_embedding_failed()
                    failed_count += 1
                    continue
        
        logger.info(f"Queued embedding generation for {processed_count} chunks (material: {material.file.name})")
        
        # Material will be marked as completed by the individual chunk tasks
        return {
            'status': 'success',
            'material_id': material_id,
            'chunks_processed': processed_count,
            'chunks_failed': failed_count
        }
        
    except SubjectMaterial.DoesNotExist:
        logger.error(f"Material with id {material_id} not found")
        return {'status': 'error', 'message': 'Material not found'}
        
    except Exception as e:
        logger.exception(f"Error processing material embeddings for {material_id}: {str(e)}")
        
        # Update material status to failed
        try:
            material = SubjectMaterial.objects.get(id=material_id)
            material.status = 'FAILED'
            material.save()
        except:
            pass
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 30  # 30, 60, 120 seconds
            logger.info(f"Retrying material embedding processing in {countdown} seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=countdown, exc=e)
        else:
            logger.error(f"Max retries exceeded for material embedding processing: {material_id}")
            return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=5)
def generate_chunk_embedding(self, chunk_id: int):
    """
    Generate embedding for a single content chunk with retry logic.
    Uses the existing ContentProcessor for consistency.
    """
    try:
        from .models import ContentChunk
        from .utils import ContentProcessor
        
        chunk = ContentChunk.objects.get(id=chunk_id)
        logger.debug(f"Generating embedding for chunk {chunk_id} (material: {chunk.material.file.name})")
        
        # Mark as pending if not already
        if chunk.embedding_status != 'pending':
            chunk.embedding_status = 'pending'
            chunk.save(update_fields=['embedding_status', 'updated_at'])
        
        # Initialize ContentProcessor with memory-conscious settings
        processor = ContentProcessor(batch_size=1, memory_threshold=0.9)  # Single chunk processing
        
        # Generate embedding for chunk content
        embedding = processor.model.encode(chunk.content)
        
        # Update chunk with embedding and mark as completed
        chunk.embedding_vector = embedding.tolist()
        chunk.mark_embedding_completed()
        
        logger.debug(f"Successfully generated embedding for chunk {chunk_id}")
        
        # Check if all chunks in the material are now completed
        material = chunk.material
        pending_chunks = ContentChunk.objects.filter(
            material=material,
            embedding_status__in=['pending', 'failed']
        ).count()
        
        if pending_chunks == 0:
            # All chunks completed, update material status
            material.status = 'COMPLETED'
            material.save()
            logger.info(f"All embeddings completed for material: {material.file.name}")
        
        return {
            'status': 'success',
            'chunk_id': chunk_id,
            'material_id': material.id,
            'embedding_length': len(embedding)
        }
        
    except ContentChunk.DoesNotExist:
        logger.error(f"ContentChunk with id {chunk_id} not found")
        return {'status': 'error', 'message': 'Content chunk not found'}
        
    except Exception as e:
        logger.exception(f"Error generating embedding for chunk {chunk_id}: {str(e)}")
        
        # Mark chunk as failed
        try:
            chunk = ContentChunk.objects.get(id=chunk_id)
            chunk.mark_embedding_failed()
        except:
            pass
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 10  # 10, 20, 40, 80, 160 seconds
            logger.info(f"Retrying chunk embedding generation in {countdown} seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=countdown, exc=e)
        else:
            logger.error(f"Max retries exceeded for chunk embedding generation: {chunk_id}")
            return {'status': 'error', 'message': str(e)}


@shared_task
def update_existing_material_embeddings(material_id: int):
    """
    Update embeddings for an existing material that already has content chunks.
    Useful for backfilling embeddings or re-processing failed chunks.
    """
    try:
        from .models import SubjectMaterial, ContentChunk
        
        material = SubjectMaterial.objects.get(id=material_id)
        logger.info(f"Updating embeddings for existing material: {material.file.name}")
        
        # Find chunks that need embedding updates
        chunks_needing_update = ContentChunk.objects.filter(
            material=material
        ).filter(
            models.Q(embedding_vector__isnull=True) |
            models.Q(embedding_status='failed')
        )
        
        update_count = chunks_needing_update.count()
        
        if update_count == 0:
            logger.info(f"No chunks need embedding updates for material: {material.file.name}")
            return {
                'status': 'success',
                'material_id': material_id,
                'chunks_updated': 0,
                'message': 'No chunks needed updates'
            }
        
        logger.info(f"Updating embeddings for {update_count} chunks")
        
        # Reset chunks to pending status and queue for processing
        chunks_needing_update.update(embedding_status='pending')
        
        # Process through the material embeddings task
        process_material_embeddings.delay(material_id)
        
        return {
            'status': 'success',
            'material_id': material_id,
            'chunks_updated': update_count
        }
        
    except SubjectMaterial.DoesNotExist:
        logger.error(f"Material with id {material_id} not found")
        return {'status': 'error', 'message': 'Material not found'}
        
    except Exception as e:
        logger.exception(f"Error updating material embeddings for {material_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)} 