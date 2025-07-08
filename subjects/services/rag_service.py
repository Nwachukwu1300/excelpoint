import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from django.conf import settings

from .vector_search import VectorSearchService
from ..models import Subject

logger = logging.getLogger(__name__)


class RAGService:
    """
    Retrieval-Augmented Generation service for XP chatbot.
    Combines vector search with OpenAI's language model to provide
    contextual responses based on subject materials.
    """
    
    def __init__(self):
        """Initialize the RAG service with required components."""
        self.vector_service = VectorSearchService()
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # Configuration parameters
        self.max_context_length = 3000  # Maximum characters for context
        self.max_chat_history = 10      # Maximum chat exchanges to include
        self.search_top_k = 5           # Number of chunks to retrieve
        self.search_threshold = 0.35    # Minimum similarity threshold (optimized for recall)
        
    def generate_response(
        self, 
        query: str, 
        subject_id: int, 
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a response to a user query using RAG pipeline.
        
        Args:
            query: The user's question/query
            subject_id: ID of the subject to search within  
            chat_history: Previous conversation history (optional)
            user_id: ID of the user making the request (for logging)
            
        Returns:
            Dictionary containing response, metadata, and retrieved chunks
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If response generation fails
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
                
            if not Subject.objects.filter(id=subject_id).exists():
                raise ValueError(f"Subject with ID {subject_id} does not exist")
            
            query = query.strip()
            chat_history = chat_history or []
            
            logger.info(f"Generating response for query: '{query[:50]}...' (subject: {subject_id})")
            
            # Step 1: Perform vector search to retrieve relevant chunks
            search_results = self._retrieve_relevant_chunks(query, subject_id)
            
            # Step 2: Prepare context from retrieved chunks
            context = self._prepare_context(search_results)
            
            # Step 3: Format chat history for context
            formatted_history = self._format_chat_history(chat_history)
            
            # Step 4: Generate response using OpenAI
            response_data = self._generate_llm_response(
                query=query,
                context=context,
                chat_history=formatted_history,
                subject_id=subject_id
            )
            
            # Step 5: Get subject information for fallback messages
            subject_name = self._get_subject_name(subject_id)
            
            # Step 6: Validate and post-process response
            validated_response = self._validate_response(response_data['content'], context, subject_name, query, chat_history)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Compile final response with metadata
            result = {
                'response': validated_response,
                'retrieved_chunks': search_results,
                'context_used': bool(context.strip()),
                'response_time': response_time,
                'metadata': {
                    'subject_id': subject_id,
                    'user_id': user_id,
                    'chunks_found': len(search_results),
                    'model_used': self.model,
                    'tokens_used': response_data.get('usage', {}),
                    'timestamp': time.time()
                }
            }
            
            logger.info(f"Successfully generated response in {response_time:.2f}s "
                       f"(chunks: {len(search_results)}, subject: {subject_id})")
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error generating response for subject {subject_id}: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def _retrieve_relevant_chunks(self, query: str, subject_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve relevant content chunks using vector search.
        
        Args:
            query: The user's query
            subject_id: ID of the subject to search within
            
        Returns:
            List of relevant chunks with metadata
        """
        try:
            chunks = self.vector_service.search_by_query(
                query_text=query,
                subject_id=subject_id,
                top_k=self.search_top_k,
                threshold=self.search_threshold
            )
            
            logger.debug(f"Retrieved {len(chunks)} relevant chunks for query")
            return chunks
            
        except Exception as e:
            logger.warning(f"Vector search failed for subject {subject_id}: {str(e)}")
            return []  # Return empty list instead of failing
    
    def _prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Prepare context from search results for the LLM.
        
        Args:
            search_results: List of retrieved chunks with metadata
            
        Returns:
            Formatted context string
        """
        if not search_results:
            return ""
        
        try:
            context_parts = []
            total_length = 0
            
            for i, chunk in enumerate(search_results):
                # Format each chunk with source attribution
                chunk_text = chunk['content'].strip()
                material_name = chunk.get('material_name', 'Unknown')
                similarity_score = chunk.get('similarity_score', 0.0)
                
                # Create formatted chunk with metadata
                formatted_chunk = f"[Source: {material_name}]\n{chunk_text}\n"
                
                # Check if adding this chunk would exceed context limit
                if total_length + len(formatted_chunk) > self.max_context_length:
                    logger.debug(f"Context limit reached, stopping at {i} chunks")
                    break
                
                context_parts.append(formatted_chunk)
                total_length += len(formatted_chunk)
            
            context = "\n".join(context_parts)
            logger.debug(f"Prepared context with {len(context_parts)} chunks ({len(context)} characters)")
            
            return context
            
        except Exception as e:
            logger.error(f"Error preparing context: {str(e)}")
            return ""
    
    def _format_chat_history(self, chat_history: List[Dict[str, str]]) -> str:
        """
        Format chat history for inclusion in the prompt.
        
        Args:
            chat_history: List of previous chat exchanges
            
        Returns:
            Formatted chat history string
        """
        if not chat_history:
            return ""
        
        try:
            # Limit history to recent exchanges
            recent_history = chat_history[-self.max_chat_history:]
            
            formatted_exchanges = []
            for exchange in recent_history:
                user_msg = exchange.get('user', '').strip()
                assistant_msg = exchange.get('assistant', '').strip()
                
                if user_msg and assistant_msg:
                    formatted_exchanges.append(f"User: {user_msg}")
                    formatted_exchanges.append(f"XP: {assistant_msg}")
            
            if formatted_exchanges:
                history_str = "\n".join(formatted_exchanges)
                logger.debug(f"Formatted chat history with {len(recent_history)} exchanges")
                return history_str
            
            return ""
            
        except Exception as e:
            logger.error(f"Error formatting chat history: {str(e)}")
            return ""
    
    def _generate_llm_response(
        self, 
        query: str, 
        context: str, 
        chat_history: str,
        subject_id: int
    ) -> Dict[str, Any]:
        """
        Generate response using OpenAI's language model.
        
        Args:
            query: User's query
            context: Prepared context from retrieved chunks
            chat_history: Formatted chat history
            subject_id: ID of the subject
            
        Returns:
            Dictionary with response content and usage metadata
        """
        try:
            # Build system prompt with subject context
            subject_name = self._get_subject_name(subject_id)
            system_prompt = self._get_system_prompt(subject_name)
            
            # Build user prompt with context and history
            user_prompt = self._build_user_prompt(query, context, chat_history)
            
            # Make OpenAI API call
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Lower temperature to reduce creativity and general knowledge responses
                max_tokens=500,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract response data
            content = response.choices[0].message.content
            usage = response.usage._asdict() if hasattr(response.usage, '_asdict') else {}
            
            logger.debug(f"OpenAI response generated (tokens: {usage.get('total_tokens', 'unknown')})")
            
            return {
                'content': content,
                'usage': usage,
                'model': self.model
            }
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise Exception(f"Language model response generation failed: {str(e)}")
    
    def _get_system_prompt(self, subject_name: str = "this subject") -> str:
        """
        Get the system prompt that defines XP's behavior.
        
        Args:
            subject_name: Name of the subject for context
            
        Returns:
            System prompt string
        """
        return f"""You are XP, a knowledgeable and helpful {subject_name} assistant. You help users learn and understand {subject_name} concepts effectively.

CORE APPROACH:
- Be helpful, accurate, and educational in all responses
- When relevant materials are provided in the context, prioritize and reference them
- Provide clear, well-structured explanations that help users understand concepts
- Use your knowledge to fill gaps and provide comprehensive answers
- Avoid hallucinations - if you're uncertain about specific details, acknowledge it

USING MATERIALS:
- When uploaded materials contain relevant information, incorporate and cite them
- Use materials as primary sources when available and relevant
- Supplement material information with clear explanations when helpful
- Reference specific sources when quoting or summarizing from materials

CONVERSATION HANDLING:
- Pay attention to conversation history and context
- Handle follow-up requests appropriately (shorter, longer, clarify, more detail)
- When asked to modify responses: adjust length, style, or detail level as requested
- Maintain conversation continuity and remember what was discussed

RESPONSE STYLE:
- Be conversational and approachable
- Provide practical examples when helpful
- Break down complex concepts into understandable parts
- Encourage learning and curiosity
- If materials don't cover a topic fully, supplement with accurate general knowledge

REMEMBER: Your goal is to be a helpful, accurate, and educational assistant that enhances learning using available materials while providing comprehensive support."""
    
    def _build_user_prompt(self, query: str, context: str, chat_history: str) -> str:
        """
        Build the user prompt with query, context, and history.
        
        Args:
            query: User's query
            context: Prepared context from chunks
            chat_history: Formatted chat history
            
        Returns:
            Complete user prompt
        """
        prompt_parts = []
        
        # Add chat history if available
        if chat_history:
            prompt_parts.append(f"Previous conversation:\n{chat_history}\n")
        
        # Add context if available
        if context:
            prompt_parts.append(f"Relevant uploaded materials:\n{context}\n")
        
        # Add current query
        prompt_parts.append(f"User question: {query}")
        
        return "\n".join(prompt_parts)
    
    def _get_subject_name(self, subject_id: int) -> str:
        """
        Get the subject name for creating subject-specific messages.
        
        Args:
            subject_id: ID of the subject
            
        Returns:
            Subject name or generic term if not found
        """
        try:
            from subjects.models import Subject
            subject = Subject.objects.get(id=subject_id)
            return subject.name
        except Exception as e:
            logger.warning(f"Could not get subject name for ID {subject_id}: {str(e)}")
            return "this subject"
    
    def _get_subject_specific_fallback(self, subject_name: str) -> str:
        """
        Generate a helpful fallback message.
        
        Args:
            subject_name: Name of the subject
            
        Returns:
            Encouraging fallback message
        """
        return f"I'd be happy to help you with {subject_name}! Could you please provide more details about what you'd like to learn or understand better?"
    
    def _is_conversational_query(self, query: str) -> bool:
        """
        Check if a query is conversational rather than academic.
        
        Args:
            query: The user's query
            
        Returns:
            True if the query is conversational
        """
        conversational_patterns = [
            # Greetings
            r'\b(hi|hello|hey|good morning|good afternoon|good evening)\b',
            # Thanks and politeness
            r'\b(thank you|thanks|please|excuse me)\b',
            # Questions about the bot/help
            r'\b(what can you|how can you|what do you|who are you|what are you)\b',
            r'\b(what can.*help|how can.*help|can you help|help me)\b',
            # General inquiries
            r'\b(how are you)\b',
            # Short informal responses
            r'^(ok|okay|yes|no|sure|great|cool)$'
        ]
        
        import re
        query_lower = query.lower().strip()
        
        # Check patterns regardless of length for conversational queries
        for pattern in conversational_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Additional check for very short common phrases
        if len(query_lower.split()) <= 3:
            short_conversational = [
                r'^(hi|hello|hey|thanks|thank you)!?$',
                r'^(yes|no|ok|okay|sure|great|cool)!?$'
            ]
            for pattern in short_conversational:
                if re.search(pattern, query_lower):
                    return True
        
        return False

    def _is_followup_request(self, query: str, chat_history: List[Dict[str, str]]) -> bool:
        """
        Check if a query is a follow-up request to modify a previous response.
        
        Args:
            query: The user's query
            chat_history: Previous conversation exchanges
            
        Returns:
            True if the query is a follow-up request
        """
        import re
        
        # Return False if no chat history
        if not chat_history:
            return False
        
        query_lower = query.lower().strip()
        
        # Patterns that indicate follow-up requests
        followup_patterns = [
            # Length modification requests
            r'\b(shorter|briefer|more concise|less detail|summarize|brief)\b',
            r'\b(longer|more detail|elaborate|expand|explain more|in depth)\b',
            
            # Format modification requests  
            r'\b(can you (be )?respond|could you respond|respond)\b.*\b(shorter|longer|differently)\b',
            r'\b(make it|make that)\b.*\b(shorter|longer|simpler|clearer)\b',
            
            # Style modification requests
            r'\b(simpler|easier|clearer|more technical|less technical)\b',
            r'\b(in other words|rephrase|reword|differently)\b',
            
            # Direct modification requests
            r'(shorten|lengthen|clarify|simplify) (it|that|your (answer|response))',
            r'\b(too long|too short|too complex|too simple)\b',
            
            # Question about previous response
            r'\b(what do you mean|can you clarify|what does that mean)\b',
            r'\b(i don\'t understand|confused about|unclear)\b',
            
            # Request for examples or more info about previous topic
            r'\b(give me an example|show me an example|for example)\b',
            r'\b(tell me more about|more about|about that)\b'
        ]
        
        # Check for follow-up patterns
        for pattern in followup_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Additional heuristic: Short queries with context words
        if len(query_lower.split()) <= 8:
            context_indicators = [
                r'\b(that|it|this|your response|your answer)\b',
                r'\b(above|previous|earlier|before)\b'
            ]
            for pattern in context_indicators:
                if re.search(pattern, query_lower):
                    return True
        
        return False

    def _validate_response(self, response: str, context: str, subject_name: str = "this subject", query: str = "", chat_history: List[Dict[str, str]] = None) -> str:
        """
        Validate and post-process the generated response.
        
        Args:
            response: Generated response from LLM
            context: Context that was provided to LLM
            subject_name: Name of the subject for specific fallback messages
            query: Original user query for conversational detection
            chat_history: Previous conversation exchanges
            
        Returns:
            Validated response
        """
        # Simple fallback for empty responses
        if not response or not response.strip():
            return f"I'd be happy to help with {subject_name}! Could you please clarify your question or provide more details?"
        
        response = response.strip()
        
        # Basic safety check - only block clearly inappropriate content
        if self._contains_severe_issues(response):
            logger.warning("Response contains concerning content")
            return f"I encountered an issue generating a response. Please try rephrasing your question about {subject_name}."
        
        # For all other cases, allow the response through
        return response
    
    def _contains_severe_issues(self, response: str) -> bool:
        """
        Check for only severe issues that should be blocked.
        
        Args:
            response: The response to check
            
        Returns:
            True if severe issues found
        """
        import re
        
        # Only block clearly inappropriate content
        severe_patterns = [
            # AI self-references that are concerning
            r'\b(I am an AI|I\'m an AI|as an AI)\b',
            r'\b(I don\'t have access|I cannot access|I can\'t access)\b',
            r'\b(I was trained|my training data|language model)\b',
            
            # Inappropriate responses
            r'\b(I cannot help|I can\'t help|I\'m not able to help)\b.*\b(upload|materials|documents)\b'
        ]
        
        response_lower = response.lower()
        for pattern in severe_patterns:
            if re.search(pattern, response_lower, re.IGNORECASE):
                return True
        
        return False

    def _contains_general_knowledge_indicators(self, response: str) -> bool:
        """
        Check if response contains indicators of general knowledge usage.
        
        Args:
            response: The response to check
            
        Returns:
            True if general knowledge indicators found
        """
        # Expanded list of general knowledge indicators
        general_knowledge_indicators = [
            # Common general knowledge phrases
            "generally speaking", "in general", "typically", "usually", "commonly",
            "as we know", "it is well known", "according to", "studies show",
            "research indicates", "experts say", "it is important to note",
            "as a general rule", "in most cases", "traditionally", "historically",
            "it's widely accepted", "the consensus is", "most people believe",
            "everyone knows", "it's obvious", "obviously", "clearly",
            
            # Academic/external reference patterns
            "published research", "academic studies", "scientific literature",
            "peer-reviewed", "according to researchers", "studies have shown",
            "data suggests", "statistics show", "surveys indicate",
            
            # Authority/external source patterns  
            "industry standards", "best practices", "widely recommended",
            "standard procedure", "conventional wisdom", "common practice",
            "established method", "proven technique", "well-documented"
        ]
        
        response_lower = response.lower()
        for indicator in general_knowledge_indicators:
            if indicator in response_lower:
                return True
        
        return False
    
    def _is_response_grounded_in_context(self, response: str, context: str) -> bool:
        """
        Check if response content is grounded in the provided context.
        
        Args:
            response: The response to validate
            context: The context that was provided
            
        Returns:
            True if response appears grounded in context
        """
        try:
            # Simple heuristic: Check if key terms from response appear in context
            # Remove common stop words and focus on content words
            import re
            
            # Extract meaningful words from response (excluding common words)
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
            
            # Extract words from response (alphanumeric, 3+ characters)
            response_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', response.lower()))
            response_content_words = response_words - stop_words
            
            if not response_content_words:
                return True  # If no content words, let it pass (likely a simple response)
            
            # Extract words from context
            context_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', context.lower()))
            
            # Check if significant portion of response words appear in context
            overlap = response_content_words.intersection(context_words)
            overlap_ratio = len(overlap) / len(response_content_words) if response_content_words else 0
            
            # Require at least 50% overlap of content words for proper grounding
            return overlap_ratio >= 0.5
            
        except Exception as e:
            logger.error(f"Error in content grounding validation: {str(e)}")
            return True  # If validation fails, err on the side of allowing the response
    
    def _contains_prohibited_patterns(self, response: str) -> bool:
        """
        Check for patterns that indicate general knowledge or inappropriate content.
        
        Args:
            response: The response to check
            
        Returns:
            True if prohibited patterns found
        """
        # Patterns that suggest general knowledge or inappropriate responses
        prohibited_patterns = [
            # External references
            r'\b(wikipedia|google|internet|web search|online|website)\b',
            r'\b(I learned|I know|I understand|from my training)\b',
            r'\b(AI assistant|language model|artificial intelligence)\b',
            r'\b(as an AI|I am an AI|I\'m an AI)\b',
            
            # General knowledge assertions without source
            r'\b(everyone knows|it\'s obvious|clearly|obviously)\b',
            r'\b(fundamental principle|basic concept|standard definition)\b',
            
            # Time-based references that couldn't be in materials
            r'\b(currently|nowadays|these days|in recent years|latest)\b',
            r'\b(as of \d{4}|since \d{4}|until \d{4})\b'
        ]
        
        import re
        
        for pattern in prohibited_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        return False
    
    def get_service_stats(self, subject_id: int) -> Dict[str, Any]:
        """
        Get statistics about the RAG service for a specific subject.
        
        Args:
            subject_id: ID of the subject
            
        Returns:
            Dictionary with service statistics
        """
        try:
            vector_stats = self.vector_service.get_search_stats(subject_id)
            
            return {
                'subject_id': subject_id,
                'vector_search': vector_stats,
                'rag_config': {
                    'model': self.model,
                    'max_context_length': self.max_context_length,
                    'search_top_k': self.search_top_k,
                    'search_threshold': self.search_threshold
                },
                'ready_for_chat': vector_stats.get('has_embeddings', False)
            }
            
        except Exception as e:
            logger.error(f"Error getting RAG stats for subject {subject_id}: {str(e)}")
            return {
                'subject_id': subject_id,
                'error': str(e),
                'ready_for_chat': False
            } 