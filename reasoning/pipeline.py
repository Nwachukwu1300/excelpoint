"""
Main reasoning pipeline orchestration.

Coordinates the full reasoning flow: classify -> rewrite -> retrieve ->
generate -> verify -> retry -> score -> assemble response.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from openai import OpenAI
from django.conf import settings

from retrieval.pipeline import PipelineManager, RetrievalPipeline, PipelineConfig
from retrieval.reranking import RankedChunk

from .classifier import (
    QueryClassifier,
    ClassificationResult,
    QueryClassificationCategory,
    ClassificationError,
)
from .rewriter import QueryRewriter, RewriteResult
from .verifier import AnswerVerifier, VerificationResult
from .confidence import ConfidenceScorer, ConfidenceScore
from .retry import RetryHandler, RetryResult
from .prompts import (
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_PROMPT_TEMPLATE,
    GENERATOR_WITH_HISTORY_TEMPLATE,
    GENERATOR_DIRECT_RESPONSE_PROMPT,
    GENERATOR_CLARIFICATION_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    """
    Complete result of the reasoning pipeline.

    Contains all inputs, intermediate outputs, and final results from
    every stage of the reasoning process.

    Attributes:
        original_query: The user's original query.
        subject_id: The subject ID that was searched.
        classification_result: Result of query classification.
        rewritten_query: The rewritten query (if applicable).
        rewrite_result: Full rewrite result object.
        pipeline_name: Name of the retrieval pipeline used.
        retrieved_chunks: List of retrieved chunks.
        generated_answer: The initial generated answer.
        verification_result: Result of answer verification.
        retry_results: List of retry attempt results.
        final_answer: The final answer used (after retries if any).
        confidence_score: The confidence score object.
        unverified_flag: Whether the answer could not be verified.
        total_latency_ms: Total end-to-end latency.
        latency_breakdown: Time spent in each stage.
    """

    # Inputs
    original_query: str
    subject_id: int

    # Classification
    classification_result: Optional[ClassificationResult] = None

    # Rewriting
    rewritten_query: Optional[str] = None
    rewrite_result: Optional[RewriteResult] = None

    # Retrieval
    pipeline_name: str = ""
    retrieved_chunks: List[RankedChunk] = field(default_factory=list)

    # Generation
    generated_answer: str = ""

    # Verification
    verification_result: Optional[VerificationResult] = None

    # Retry
    retry_results: List[RetryResult] = field(default_factory=list)

    # Final output
    final_answer: str = ""
    confidence_score: Optional[ConfidenceScore] = None
    unverified_flag: bool = False

    # Timing
    total_latency_ms: float = 0.0
    latency_breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'original_query': self.original_query,
            'subject_id': self.subject_id,
            'classification_result': (
                self.classification_result.to_dict()
                if self.classification_result else None
            ),
            'rewritten_query': self.rewritten_query,
            'rewrite_result': (
                self.rewrite_result.to_dict()
                if self.rewrite_result else None
            ),
            'pipeline_name': self.pipeline_name,
            'retrieved_chunks': [
                chunk.to_dict() if hasattr(chunk, 'to_dict') else chunk
                for chunk in self.retrieved_chunks
            ],
            'retrieved_chunk_count': len(self.retrieved_chunks),
            'generated_answer': self.generated_answer,
            'verification_result': (
                self.verification_result.to_dict()
                if self.verification_result else None
            ),
            'retry_results': [r.to_dict() for r in self.retry_results],
            'retry_count': len(self.retry_results),
            'final_answer': self.final_answer,
            'confidence_score': (
                self.confidence_score.to_dict()
                if self.confidence_score else None
            ),
            'unverified_flag': self.unverified_flag,
            'total_latency_ms': self.total_latency_ms,
            'latency_breakdown': self.latency_breakdown,
        }


class ReasoningError(Exception):
    """Raised when the reasoning pipeline fails."""

    pass


class ReasoningPipeline:
    """
    Main reasoning pipeline.

    Orchestrates the full reasoning flow:
    1. Classify query
    2. If DIRECT_RESPONSE: generate directly, skip retrieval
    3. If CLARIFICATION_REQUIRED: return clarification request
    4. If RETRIEVAL_REQUIRED: continue
    5. Rewrite query for better retrieval
    6. Retrieve relevant chunks using Stage 1 pipeline
    7. Generate answer from chunks
    8. Verify answer against chunks
    9. Retry if verification fails (max 2 times)
    10. Score confidence
    11. Assemble and return ReasoningResult

    Attributes:
        default_pipeline_name: Default retrieval pipeline to use.
        faithfulness_threshold: Threshold for triggering retries.
        max_retries: Maximum retry attempts.
    """

    def __init__(
        self,
        default_pipeline_name: Optional[str] = None,
        faithfulness_threshold: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initialize the reasoning pipeline.

        Args:
            default_pipeline_name: Default retrieval pipeline to use.
                Defaults to settings.REASONING_DEFAULT_PIPELINE or 'default'.
            faithfulness_threshold: Threshold for triggering retries.
            max_retries: Maximum retry attempts.
        """
        self.default_pipeline_name = default_pipeline_name or getattr(
            settings, 'REASONING_DEFAULT_PIPELINE', 'default'
        )
        self.faithfulness_threshold = faithfulness_threshold or getattr(
            settings, 'REASONING_FAITHFULNESS_THRESHOLD', 0.7
        )
        self.max_retries = max_retries or getattr(
            settings, 'REASONING_MAX_RETRIES', 2
        )

        # Lazy-initialized components
        self._classifier: Optional[QueryClassifier] = None
        self._rewriter: Optional[QueryRewriter] = None
        self._verifier: Optional[AnswerVerifier] = None
        self._confidence_scorer: Optional[ConfidenceScorer] = None
        self._retry_handler: Optional[RetryHandler] = None
        self._openai_client: Optional[OpenAI] = None

        # Model settings
        self._model = getattr(
            settings, 'REASONING_LLM_MODEL',
            getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        )
        self._generator_temperature = getattr(
            settings, 'REASONING_GENERATOR_TEMPERATURE', 0.4
        )

    def _get_classifier(self) -> QueryClassifier:
        """Get or create the query classifier."""
        if self._classifier is None:
            self._classifier = QueryClassifier()
        return self._classifier

    def _get_rewriter(self) -> QueryRewriter:
        """Get or create the query rewriter."""
        if self._rewriter is None:
            self._rewriter = QueryRewriter()
        return self._rewriter

    def _get_verifier(self) -> AnswerVerifier:
        """Get or create the answer verifier."""
        if self._verifier is None:
            self._verifier = AnswerVerifier()
        return self._verifier

    def _get_confidence_scorer(self) -> ConfidenceScorer:
        """Get or create the confidence scorer."""
        if self._confidence_scorer is None:
            self._confidence_scorer = ConfidenceScorer()
        return self._confidence_scorer

    def _get_retry_handler(self) -> RetryHandler:
        """Get or create the retry handler."""
        if self._retry_handler is None:
            self._retry_handler = RetryHandler(
                faithfulness_threshold=self.faithfulness_threshold,
                max_retries=self.max_retries,
            )
        return self._retry_handler

    def _get_openai_client(self) -> OpenAI:
        """Get or create the OpenAI client."""
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    def run(
        self,
        query: str,
        subject_id: int,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        pipeline_name: Optional[str] = None,
    ) -> ReasoningResult:
        """
        Run the full reasoning pipeline.

        Args:
            query: User's query.
            subject_id: Subject to search within.
            conversation_history: Previous conversation exchanges.
            pipeline_name: Retrieval pipeline to use.

        Returns:
            ReasoningResult with all outputs and metrics.

        Raises:
            ReasoningError: If the pipeline fails critically.
        """
        total_start = time.perf_counter()
        latency_breakdown: Dict[str, float] = {}

        if not query or not query.strip():
            raise ReasoningError("Query cannot be empty")

        query = query.strip()
        pipeline_name = pipeline_name or self.default_pipeline_name

        result = ReasoningResult(
            original_query=query,
            subject_id=subject_id,
            pipeline_name=pipeline_name,
        )

        try:
            # Step 1: Classification
            logger.info(f"Starting reasoning pipeline for query: '{query[:50]}...'")
            classification_result, classification_time = self._classify_query(query)
            result.classification_result = classification_result
            latency_breakdown['classification_ms'] = classification_time

            # Handle non-retrieval cases
            if classification_result.category == QueryClassificationCategory.DIRECT_RESPONSE:
                logger.info("Query classified as DIRECT_RESPONSE, skipping retrieval")
                answer, gen_time = self._handle_direct_response(query)
                result.generated_answer = answer
                result.final_answer = answer
                latency_breakdown['generation_ms'] = gen_time

                # Create simple verification for direct responses
                result.verification_result = VerificationResult(
                    grounded=True,
                    supported_claims=[],
                    unsupported_claims=[],
                    faithfulness_score=1.0,
                    reasoning="Direct response, no source verification needed",
                )
                result.confidence_score = ConfidenceScore(
                    final_score=0.9,
                    score_breakdown={'direct_response': 0.9},
                    interpretation="HIGH_CONFIDENCE",
                )
                result.total_latency_ms = (time.perf_counter() - total_start) * 1000
                result.latency_breakdown = latency_breakdown
                return result

            if classification_result.category == QueryClassificationCategory.CLARIFICATION_REQUIRED:
                logger.info("Query classified as CLARIFICATION_REQUIRED")
                answer, gen_time = self._handle_clarification(query)
                result.generated_answer = answer
                result.final_answer = answer
                latency_breakdown['generation_ms'] = gen_time

                result.verification_result = VerificationResult(
                    grounded=True,
                    supported_claims=[],
                    unsupported_claims=[],
                    faithfulness_score=1.0,
                    reasoning="Clarification request, no source verification needed",
                )
                result.confidence_score = ConfidenceScore(
                    final_score=0.9,
                    score_breakdown={'clarification_request': 0.9},
                    interpretation="HIGH_CONFIDENCE",
                )
                result.total_latency_ms = (time.perf_counter() - total_start) * 1000
                result.latency_breakdown = latency_breakdown
                return result

            # Step 2: Query Rewriting
            rewrite_result, rewrite_time = self._rewrite_query(
                query, conversation_history
            )
            result.rewrite_result = rewrite_result
            result.rewritten_query = rewrite_result.rewritten_query
            latency_breakdown['rewrite_ms'] = rewrite_time

            # Step 3: Retrieval
            chunks, retrieval_time = self._retrieve_chunks(
                rewrite_result.rewritten_query,
                subject_id,
                pipeline_name,
            )
            result.retrieved_chunks = chunks
            latency_breakdown['retrieval_ms'] = retrieval_time

            # Step 4: Answer Generation
            answer, gen_time = self._generate_answer(
                rewrite_result.rewritten_query,
                chunks,
                conversation_history,
            )
            result.generated_answer = answer
            latency_breakdown['generation_ms'] = gen_time

            # Step 5: Verification
            verification, verify_time = self._verify_answer(answer, chunks)
            result.verification_result = verification
            latency_breakdown['verification_ms'] = verify_time

            # Step 6: Retry if needed
            retry_results = []
            current_answer = answer
            current_verification = verification
            current_chunks = chunks

            retry_handler = self._get_retry_handler()
            attempt = 1

            while retry_handler.should_retry(current_verification, attempt):
                attempt += 1
                logger.info(f"Starting retry attempt #{attempt - 1}")

                # Get retry query
                retry_start = time.perf_counter()
                retry_partial = retry_handler.handle(
                    original_query=query,
                    verification=current_verification,
                    pipeline_name=pipeline_name,
                    subject_id=subject_id,
                    attempt_number=attempt - 1,
                )

                # Re-retrieve with rewritten query
                retry_chunks, _ = self._retrieve_chunks(
                    retry_partial.rewritten_query,
                    subject_id,
                    pipeline_name,
                )
                retry_partial.retrieved_chunks = retry_chunks

                # Re-generate answer
                retry_answer, _ = self._generate_answer(
                    retry_partial.rewritten_query,
                    retry_chunks,
                    conversation_history,
                )
                retry_partial.generated_answer = retry_answer

                # Re-verify
                retry_verification, _ = self._verify_answer(retry_answer, retry_chunks)
                retry_partial.verification_result = retry_verification

                # Check if successful
                if (retry_verification.grounded and
                    retry_verification.faithfulness_score >= self.faithfulness_threshold):
                    retry_partial.success = True

                retry_time = (time.perf_counter() - retry_start) * 1000
                latency_breakdown[f'retry_{attempt - 1}_ms'] = retry_time

                retry_results.append(retry_partial)

                # Update current values for next iteration
                current_answer = retry_answer
                current_verification = retry_verification
                current_chunks = retry_chunks

                if retry_partial.success:
                    break

            result.retry_results = retry_results

            # Step 7: Select best result
            final_answer, final_verification, is_verified = retry_handler.select_best_result(
                initial_answer=answer,
                initial_verification=verification,
                retry_results=retry_results,
            )
            result.final_answer = final_answer
            result.verification_result = final_verification
            result.unverified_flag = not is_verified

            # Step 8: Confidence Scoring
            scorer = self._get_confidence_scorer()
            confidence_score = scorer.score(
                verification=final_verification,
                chunks=current_chunks,
                is_first_attempt=len(retry_results) == 0,
            )
            result.confidence_score = confidence_score

            # Finalize timing
            result.total_latency_ms = (time.perf_counter() - total_start) * 1000
            result.latency_breakdown = latency_breakdown

            logger.info(
                f"Reasoning pipeline complete: confidence={confidence_score.final_score:.2f}, "
                f"verified={not result.unverified_flag}, "
                f"retries={len(retry_results)}, "
                f"latency={result.total_latency_ms:.0f}ms"
            )

            return result

        except ClassificationError as e:
            logger.error(f"Classification failed: {str(e)}")
            result.total_latency_ms = (time.perf_counter() - total_start) * 1000
            result.latency_breakdown = latency_breakdown
            raise ReasoningError(f"Query classification failed: {str(e)}")
        except Exception as e:
            logger.error(f"Reasoning pipeline error: {str(e)}")
            result.total_latency_ms = (time.perf_counter() - total_start) * 1000
            result.latency_breakdown = latency_breakdown
            raise ReasoningError(f"Reasoning pipeline failed: {str(e)}")

    def _classify_query(self, query: str) -> tuple[ClassificationResult, float]:
        """
        Classify the query.

        Returns:
            Tuple of (ClassificationResult, latency_ms).
        """
        start = time.perf_counter()
        classifier = self._get_classifier()
        result = classifier.classify(query)
        latency = (time.perf_counter() - start) * 1000
        return result, latency

    def _rewrite_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> tuple[RewriteResult, float]:
        """
        Rewrite query for retrieval.

        Returns:
            Tuple of (RewriteResult, latency_ms).
        """
        start = time.perf_counter()
        rewriter = self._get_rewriter()
        result = rewriter.rewrite(query, conversation_history)
        latency = (time.perf_counter() - start) * 1000
        return result, latency

    def _retrieve_chunks(
        self,
        query: str,
        subject_id: int,
        pipeline_name: str,
    ) -> tuple[List[RankedChunk], float]:
        """
        Retrieve relevant chunks using Stage 1 pipeline.

        Returns:
            Tuple of (chunks, latency_ms).
        """
        start = time.perf_counter()

        try:
            # Get configured pipeline from Stage 1
            pipeline = PipelineManager.get_pipeline(pipeline_name)
            retrieval_result = pipeline.search(query=query, subject_id=subject_id)
            latency = (time.perf_counter() - start) * 1000

            logger.info(
                f"Retrieved {retrieval_result.chunk_count} chunks, "
                f"top_score={retrieval_result.top_score:.3f}"
            )

            return retrieval_result.chunks, latency

        except ValueError as e:
            # Pipeline not found - try to create a default one
            logger.warning(
                f"Pipeline '{pipeline_name}' not found, using default config"
            )
            config = PipelineConfig(
                name=pipeline_name,
                description="Auto-created default pipeline",
                top_k=10,
                similarity_threshold=0.15,
            )
            pipeline = RetrievalPipeline(config)
            retrieval_result = pipeline.search(query=query, subject_id=subject_id)
            latency = (time.perf_counter() - start) * 1000

            return retrieval_result.chunks, latency

    def _generate_answer(
        self,
        query: str,
        chunks: List[RankedChunk],
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> tuple[str, float]:
        """
        Generate answer from retrieved chunks.

        Returns:
            Tuple of (answer, latency_ms).
        """
        start = time.perf_counter()
        client = self._get_openai_client()

        # Format context from chunks
        context = self._format_chunks_for_generation(chunks)

        # Build prompt
        if conversation_history and len(conversation_history) > 0:
            history_str = self._format_conversation_history(conversation_history)
            user_prompt = GENERATOR_WITH_HISTORY_TEMPLATE.format(
                conversation_history=history_str,
                context=context,
                query=query,
            )
        else:
            user_prompt = GENERATOR_USER_PROMPT_TEMPLATE.format(
                context=context,
                query=query,
            )

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._generator_temperature,
            max_tokens=1000,
        )

        answer = response.choices[0].message.content or ""
        latency = (time.perf_counter() - start) * 1000

        return answer.strip(), latency

    def _verify_answer(
        self,
        answer: str,
        chunks: List[RankedChunk],
    ) -> tuple[VerificationResult, float]:
        """
        Verify answer against chunks.

        Returns:
            Tuple of (VerificationResult, latency_ms).
        """
        start = time.perf_counter()
        verifier = self._get_verifier()
        result = verifier.verify(answer, chunks)
        latency = (time.perf_counter() - start) * 1000
        return result, latency

    def _handle_direct_response(self, query: str) -> tuple[str, float]:
        """
        Handle queries that don't need retrieval.

        Returns:
            Tuple of (answer, latency_ms).
        """
        start = time.perf_counter()
        client = self._get_openai_client()

        user_prompt = GENERATOR_DIRECT_RESPONSE_PROMPT.format(query=query)

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        answer = response.choices[0].message.content or ""
        latency = (time.perf_counter() - start) * 1000

        return answer.strip(), latency

    def _handle_clarification(self, query: str) -> tuple[str, float]:
        """
        Handle queries that need clarification.

        Returns:
            Tuple of (clarification_request, latency_ms).
        """
        start = time.perf_counter()
        client = self._get_openai_client()

        user_prompt = GENERATOR_CLARIFICATION_PROMPT.format(query=query)

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=300,
        )

        answer = response.choices[0].message.content or ""
        latency = (time.perf_counter() - start) * 1000

        return answer.strip(), latency

    def _format_chunks_for_generation(self, chunks: List[RankedChunk]) -> str:
        """Format chunks into context string for generation."""
        if not chunks:
            return "No relevant content found in study materials."

        formatted = []
        for i, chunk in enumerate(chunks[:8], 1):  # Limit to 8 chunks
            content = chunk.content
            if len(content) > 1500:
                content = content[:1500] + "..."
            formatted.append(
                f"[Source {i}: {chunk.material_name}]\n{content}"
            )

        return "\n\n---\n\n".join(formatted)

    def _format_conversation_history(
        self, history: List[Dict[str, str]]
    ) -> str:
        """Format conversation history for the prompt."""
        formatted = []
        for exchange in history[-5:]:  # Last 5 exchanges
            role = exchange.get('role', 'unknown').capitalize()
            content = exchange.get('content', '')
            if len(content) > 200:
                content = content[:200] + "..."
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
