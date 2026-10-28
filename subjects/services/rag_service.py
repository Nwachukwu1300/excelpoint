import json
import logging
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from django.conf import settings

from .vector_search import VectorSearchService
from .cache_service import ChatbotCacheService
from ..models import Subject, SubjectMaterial

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
        self.model = settings.OPENAI_MODEL
        self.cache_service = ChatbotCacheService()
        
        # Configuration parameters
        self.max_context_length = 3000  # Maximum characters for context
        self.max_chat_history = 10      # Maximum chat exchanges to include
        self.search_top_k = 5           # Number of chunks to retrieve
        self.search_threshold = 0.3     # Below this MiniLM matches are mostly noise, so treat as "not in materials"
        
    def generate_response(
        self, 
        query: str, 
        subject_id: int, 
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Answer a query and return the result dict (see respond_events for the streaming form)."""
        for kind, value in self.respond_events(query, subject_id, chat_history, user_id):
            if kind == 'result':
                return value

    def respond_events(
        self,
        query: str,
        subject_id: int,
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[int] = None,
        stream: bool = False,
    ):
        """
        Generate a response to a user query using RAG pipeline with caching, as a generator:
        ('token', text) events (the reasoning answer streams when stream=True; instant replies
        arrive as one token), then exactly one ('result', dict).
        
        Args:
            query: The user's question/query
            subject_id: ID of the subject to search within  
            chat_history: Previous conversation history (optional)
            user_id: ID of the user making the request (for caching and logging)
            
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
            
            logger.info(f"Generating response (subject: {subject_id}, user: {user_id})")  # no question text in logs
            
            # Step 1: Check cache for existing response (only for non-followup queries)
            if user_id and not self._is_followup_request(query, chat_history):
                cached_response = self.cache_service.get_cached_response(
                    user_id=user_id,
                    subject_id=subject_id,
                    question_text=query
                )
                
                if cached_response:
                    logger.info(f"Returning cached response for user {user_id}, subject {subject_id}")
                    self._log_answer(cached_response, 'cache', subject_id, user_id)
                    yield ('token', cached_response['response'])
                    yield ('result', cached_response)
                    return
            
            # Step 2: Perform vector search to retrieve relevant chunks
            search_results = self._retrieve_relevant_chunks(query, subject_id)
            
            # Step 3: Prepare context from retrieved chunks
            context = self._prepare_context(search_results)
            subject_name = self._get_subject_name(subject_id)

            is_small_talk = self._is_conversational_query(query)
            is_followup = self._is_followup_request(query, chat_history)

            # Strict RAG: nothing relevant retrieved means nothing to answer from, so skip the LLM.
            # Follow-ups ("tell me more") pass through: the reasoning rewriter resolves them from history.
            if not context.strip() and not is_small_talk and not is_followup:
                files_ready = SubjectMaterial.objects.filter(subject_id=subject_id, status='COMPLETED').exists()
                result = {
                    'response': self._get_subject_specific_fallback(subject_name) if files_ready else (
                        f"None of your files in {subject_name} are ready yet, so I have nothing to answer from. "
                        f"Open the subject's Files tab: a file may still be processing, or it may have failed."),
                    'retrieved_chunks': [],
                    'context_used': False,
                    'response_time': time.time() - start_time,
                    'metadata': {
                        'subject_id': subject_id,
                        'user_id': user_id,
                        'chunks_found': 0,
                        'model_used': None,
                        'tokens_used': {},
                        'pipeline': 'fallback',
                        'files_ready': files_ready,
                        'timestamp': time.time(),
                    },
                }
                self._log_answer(result, 'fallback', subject_id, user_id)
                yield ('token', result['response'])
                yield ('result', result)
                return
            
            # Step 4: Questions go through the reasoning pipeline (rewrite, retrieve, generate,
            # verify, retry); small talk, or a pipeline failure, uses a single grounded LLM call
            result = None
            if not is_small_talk:
                result = yield from self._reasoning_events(
                    query, subject_id, chat_history, user_id, subject_name, start_time, stream)

            if result is None:
                formatted_history = self._format_chat_history(chat_history)
                response_data = self._generate_llm_response(
                    query=query,
                    context=context,
                    chat_history=formatted_history,
                    subject_id=subject_id
                )
                validated_response = self._validate_response(response_data['content'], context, subject_name, query, chat_history)
                result = {
                    'response': validated_response,
                    'retrieved_chunks': search_results,
                    'context_used': bool(context.strip()),
                    'response_time': time.time() - start_time,
                    'metadata': {
                        'subject_id': subject_id,
                        'user_id': user_id,
                        'chunks_found': len(search_results),
                        'model_used': self.model,
                        'tokens_used': response_data.get('usage', {}),
                        'pipeline': 'single_call',
                        'timestamp': time.time()
                    }
                }
                yield ('token', result['response'])

            logger.info(f"Successfully generated response in {result['response_time']:.2f}s "
                       f"(chunks: {len(result['retrieved_chunks'])}, subject: {subject_id})")

            # Step 5: Cache material-backed answers only (non-followup)
            if user_id and result['context_used'] and not is_followup:
                try:
                    cache_success = self.cache_service.store_cached_response(
                        user_id=user_id,
                        subject_id=subject_id,
                        question_text=query,
                        response_data=result
                    )
                    if cache_success:
                        logger.debug(f"Cached response for user {user_id}, subject {subject_id}")
                    else:
                        logger.warning(f"Failed to cache response for user {user_id}, subject {subject_id}")
                except Exception as e:
                    logger.error(f"Error caching response: {str(e)}")

            self._log_answer(result, result['metadata'].get('pipeline'), subject_id, user_id)
            yield ('result', result)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error generating response for subject {subject_id}: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def _log_answer(self, result, path, subject_id, user_id):
        """One JSON line per answer so logs can be filtered and aggregated (Stage 4 observability)."""
        meta = result.get('metadata') or {}
        logger.info(json.dumps({
            'event': 'chat_answer',
            'path': path,
            'subject_id': subject_id,
            'user_id': user_id,
            'chunks': len(result.get('retrieved_chunks') or []),
            'context_used': result.get('context_used'),
            'response_s': round(result.get('response_time') or 0, 3),
            'reasoning_session_id': meta.get('reasoning_session_id'),
            'classification': meta.get('classification'),
            'verified': meta.get('verified'),
            'confidence': meta.get('confidence'),
            'retries': meta.get('retries'),
            'stage_ms': meta.get('latency_breakdown'),
        }, default=str))

    def _reasoning_events(self, query, subject_id, chat_history, user_id, subject_name, start_time, stream=False):
        """Answer via the Stage 2 reasoning pipeline, forwarding streamed tokens.
        Returns (via StopIteration) the result dict, or None if the pipeline fails."""
        from reasoning.models import ReasoningSession
        from reasoning.pipeline import ReasoningError, ReasoningPipeline

        history = []  # the pipeline expects role/content turns
        for exchange in chat_history[-self.max_chat_history:]:
            history.append({'role': 'user', 'content': exchange.get('user', '')})
            history.append({'role': 'assistant', 'content': exchange.get('assistant', '')})

        # Only follow-ups get the (extra LLM call) rewrite; standalone questions search as typed
        options = dict(query=query, subject_id=subject_id, conversation_history=history,
                       rewrite=self._is_followup_request(query, chat_history))
        streamed = False
        try:
            if stream:
                reasoning = None
                for kind, value in ReasoningPipeline().run_events(stream=True, **options):
                    if kind == 'token':
                        streamed = True
                        yield ('token', value)
                    else:
                        reasoning = value
            else:
                reasoning = ReasoningPipeline().run(**options)
        except ReasoningError as e:
            logger.warning(f"Reasoning pipeline failed, using single-call RAG instead: {e}")
            return None

        session_id = None
        try:
            session_id = str(ReasoningSession.create_from_result(reasoning).session_id)  # trace for debugging/eval
        except Exception as e:
            logger.error(f"Could not save reasoning trace: {e}")

        chunks = reasoning.final_chunks or reasoning.retrieved_chunks  # sources of the answer shown
        if not chunks and not reasoning.final_answer:
            answer = self._get_subject_specific_fallback(subject_name)
        else:
            answer = reasoning.final_answer or self._get_subject_specific_fallback(subject_name)
            if chunks and reasoning.unverified_flag:
                answer += "\n\n_Note: parts of this answer could not be fully verified against your materials._"
        if stream and not streamed:
            yield ('token', answer)  # e.g. the "not in your materials" reply when the search found nothing

        return {
            'response': answer,
            'retrieved_chunks': [
                {
                    'chunk_id': c.chunk_id,
                    'content': c.content,
                    'chunk_index': c.chunk_index,
                    'material_id': c.material_id,
                    'material_name': c.material_name,
                    'similarity_score': float(c.initial_score),
                }
                for c in chunks
            ],
            'context_used': bool(chunks),
            'response_time': time.time() - start_time,
            'metadata': {
                'subject_id': subject_id,
                'user_id': user_id,
                'chunks_found': len(chunks),
                'model_used': self.model,
                'pipeline': 'reasoning',
                'reasoning_session_id': session_id,
                'classification': 'follow_up' if reasoning.rewrite_result else 'standalone',
                'rewritten_query': reasoning.rewritten_query,
                'verified': not reasoning.unverified_flag,
                'confidence': reasoning.confidence_score.final_score if reasoning.confidence_score else None,
                'retries': len(reasoning.retry_results),
                'latency_breakdown': reasoning.latency_breakdown,
                'timestamp': time.time(),
            },
        }

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
            # Get primary search results
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
                max_completion_tokens=500,
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
        fallback = self._get_subject_specific_fallback(subject_name)
        return f"""You are XP, a study assistant for {subject_name}. You answer ONLY from the excerpts of the user's uploaded materials given in each message.

RULES:
- Use only facts stated in the provided materials. Do not add outside or general knowledge, even if you know it.
- If the materials do not contain the answer, reply with exactly: "{fallback}"
- If the materials only partly answer the question, answer that part and say what the materials don't cover.
- Cite the source file for what you use, e.g. (Source: notes.pdf).
- Greetings and small talk are fine: reply briefly and offer to help with the {subject_name} materials.
- Use the conversation history to understand follow-ups like "shorter" or "give an example", but examples must still come from the materials.
- Be clear and concise, and break complex ideas into steps."""
    
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
            prompt_parts.append(f"Relevant materials:\n{context}\n")
        
        # Add current query
        prompt_parts.append(f"Current question: {query}")
        
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
        return (
            f"I couldn't find information about that in your {subject_name} materials. "
            f"I can only help with the materials uploaded under this subject, so try uploading "
            f"documents that cover this topic or ask about something they include."
        )
    
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
        # Empty output, or an answer with no materials behind it, falls back (small talk excepted)
        if not response or not response.strip():
            return self._get_subject_specific_fallback(subject_name)
        if not context.strip() and not self._is_conversational_query(query):
            return self._get_subject_specific_fallback(subject_name)
        
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