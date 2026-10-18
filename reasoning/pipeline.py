"""
Main reasoning pipeline orchestration.

Coordinates the full reasoning flow: rewrite (follow-ups only) -> retrieve ->
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

from .rewriter import QueryRewriter, RewriteResult
from .verifier import AnswerVerifier, VerificationResult
from .confidence import ConfidenceScorer, ConfidenceScore
from .retry import RetryHandler, RetryResult
from .prompts import (
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_PROMPT_TEMPLATE,
    GENERATOR_WITH_HISTORY_TEMPLATE,
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

    # Exact LLM inputs, for the debug panel
    prompts: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'original_query': self.original_query,
            'subject_id': self.subject_id,
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
            'prompts': self.prompts,
        }


class ReasoningError(Exception):
    """Raised when the reasoning pipeline fails."""

    pass


class ReasoningPipeline:
    """
    Main reasoning pipeline.

    Orchestrates the full reasoning flow:
    1. Rewrite follow-up queries using the conversation (standalone ones skip this)
    2. Retrieve relevant chunks using Stage 1 pipeline
    3. Generate answer from chunks
    4. Verify answer against chunks
    5. Retry if verification fails (max 2 times)
    6. Score confidence
    7. Assemble and return ReasoningResult

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
        self._rewriter: Optional[QueryRewriter] = None
        self._verifier: Optional[AnswerVerifier] = None
        self._confidence_scorer: Optional[ConfidenceScorer] = None
        self._retry_handler: Optional[RetryHandler] = None
        self._openai_client: Optional[OpenAI] = None

        # Model settings
        self._model = getattr(
            settings, 'REASONING_LLM_MODEL',
            settings.OPENAI_MODEL
        )
        self._generator_temperature = getattr(
            settings, 'REASONING_GENERATOR_TEMPERATURE', 0.4
        )

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
        rewrite: Optional[bool] = None,
    ) -> ReasoningResult:
        """Run the full pipeline and return the result (see run_events for the streaming form)."""
        for kind, value in self.run_events(query, subject_id, conversation_history, pipeline_name, rewrite):
            if kind == 'result':
                return value

    def run_events(
        self,
        query: str,
        subject_id: int,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        pipeline_name: Optional[str] = None,
        rewrite: Optional[bool] = None,
        stream: bool = False,
    ):
        """
        Run the full reasoning pipeline as a generator of events:
        ('token', text) while the first answer is written (only when stream=True),
        then exactly one ('result', ReasoningResult). Retries are not streamed; if one
        wins, the result's final_answer replaces the streamed text.

        Args:
            query: User's query.
            subject_id: Subject to search within.
            conversation_history: Previous conversation exchanges.
            pipeline_name: Retrieval pipeline to use.
            rewrite: Rewrite the query with the history before searching.
                Defaults to "only when there is history"; the chat passes its follow-up check.
            stream: Stream the first answer from the model as ('token', text) events.

        Yields:
            Events as described above.

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
            logger.info(f"Starting reasoning pipeline for query: '{query[:50]}...'")

            # Step 1: Rewrite only follow-ups ("the second one"), which need the history to search well.
            # Standalone questions search fine as typed, so they skip this LLM call.
            if rewrite is None:
                rewrite = bool(conversation_history)
            search_query = query
            if rewrite:
                rewrite_result, rewrite_time = self._rewrite_query(query, conversation_history)
                result.rewrite_result = rewrite_result
                search_query = rewrite_result.rewritten_query
                latency_breakdown['rewrite_ms'] = rewrite_time
            result.rewritten_query = search_query

            # Step 2: Retrieval
            chunks, retrieval_time, retrieval_timings = self._retrieve_chunks(
                search_query,
                subject_id,
                pipeline_name,
            )
            result.retrieved_chunks = chunks
            latency_breakdown['retrieval_ms'] = retrieval_time
            latency_breakdown.update(retrieval_timings)

            if not chunks:
                # Empty final_answer + no chunks tells the caller to use its "not in your materials" reply
                logger.info("No chunks retrieved; skipping generation")
                result.unverified_flag = True
                result.total_latency_ms = (time.perf_counter() - total_start) * 1000
                result.latency_breakdown = latency_breakdown
                yield ('result', result)
                return

            # Step 3: Answer Generation
            if stream:
                answer, gen_time, messages = yield from self._stream_answer(search_query, chunks, conversation_history)
            else:
                answer, gen_time, messages = self._generate_answer(search_query, chunks, conversation_history)
            result.prompts['generation'] = messages
            result.generated_answer = answer
            latency_breakdown['generation_ms'] = gen_time

            # Step 4: Verification
            verification, verify_time = self._verify_answer(answer, chunks)
            result.verification_result = verification
            latency_breakdown['verification_ms'] = verify_time

            # Step 5: Retry if needed
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
                retry_chunks, _, _ = self._retrieve_chunks(
                    retry_partial.rewritten_query,
                    subject_id,
                    pipeline_name,
                )
                retry_partial.retrieved_chunks = retry_chunks

                # Re-generate answer
                retry_answer, _, retry_messages = self._generate_answer(
                    retry_partial.rewritten_query,
                    retry_chunks,
                    conversation_history,
                )
                result.prompts[f'generation_retry_{attempt - 1}'] = retry_messages
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

            # Step 6: Select best result
            final_answer, final_verification, is_verified = retry_handler.select_best_result(
                initial_answer=answer,
                initial_verification=verification,
                retry_results=retry_results,
            )
            result.final_answer = final_answer
            result.verification_result = final_verification
            result.unverified_flag = not is_verified

            # Step 7: Confidence Scoring
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

            yield ('result', result)

        except Exception as e:
            logger.error(f"Reasoning pipeline error: {str(e)}")
            result.total_latency_ms = (time.perf_counter() - total_start) * 1000
            result.latency_breakdown = latency_breakdown
            raise ReasoningError(f"Reasoning pipeline failed: {str(e)}")

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
    ) -> tuple[List[RankedChunk], float, Dict[str, float]]:
        """
        Retrieve relevant chunks using Stage 1 pipeline.

        Returns:
            Tuple of (chunks, latency_ms, per-stage timings).
        """
        start = time.perf_counter()

        try:
            pipeline = PipelineManager.get_pipeline(pipeline_name)
        except ValueError:
            # Only "pipeline not configured" falls back; real search errors must surface
            logger.warning(f"Pipeline '{pipeline_name}' not found, using default config")
            pipeline = RetrievalPipeline(PipelineConfig(
                name=pipeline_name,
                description="Auto-created default pipeline",
                top_k=5,
                similarity_threshold=0.3,  # same cut-off as the chat's strict RAG gate
            ))

        retrieval_result = pipeline.search(query=query, subject_id=subject_id)
        latency = (time.perf_counter() - start) * 1000
        logger.info(f"Retrieved {retrieval_result.chunk_count} chunks, top_score={retrieval_result.top_score:.3f}")

        timings = {
            'embedding_ms': retrieval_result.embedding_latency_ms,
            'search_ms': retrieval_result.search_latency_ms,
        }
        if retrieval_result.reranking_latency_ms is not None:
            timings['reranking_ms'] = retrieval_result.reranking_latency_ms
        return retrieval_result.chunks, latency, timings

    def _generate_answer(
        self,
        query: str,
        chunks: List[RankedChunk],
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> tuple[str, float, List[Dict[str, str]]]:
        """
        Generate answer from retrieved chunks.

        Returns:
            Tuple of (answer, latency_ms, the messages sent to the model).
        """
        start = time.perf_counter()
        client = self._get_openai_client()
        messages = self._generation_messages(query, chunks, conversation_history)
        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._generator_temperature,
            max_completion_tokens=1000,
        )

        answer = response.choices[0].message.content or ""
        latency = (time.perf_counter() - start) * 1000

        return answer.strip(), latency, messages

    def _stream_answer(self, query, chunks, conversation_history):
        """Like _generate_answer, but yields ('token', text) as the model writes; returns the same tuple."""
        start = time.perf_counter()
        messages = self._generation_messages(query, chunks, conversation_history)
        response = self._get_openai_client().chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._generator_temperature,
            max_completion_tokens=1000,
            stream=True,
        )
        parts = []
        for chunk in response:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                parts.append(delta)
                yield ('token', delta)
        return ''.join(parts).strip(), (time.perf_counter() - start) * 1000, messages

    def _generation_messages(self, query, chunks, conversation_history):
        """System + user messages for answer generation (shared by streamed and plain calls)."""
        context = self._format_chunks_for_generation(chunks)
        if conversation_history:
            user_prompt = GENERATOR_WITH_HISTORY_TEMPLATE.format(
                conversation_history=self._format_conversation_history(conversation_history),
                context=context,
                query=query,
            )
        else:
            user_prompt = GENERATOR_USER_PROMPT_TEMPLATE.format(context=context, query=query)
        return [
            {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

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
