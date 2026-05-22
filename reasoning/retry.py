"""
Retry handling for failed verifications.

Handles retry logic when answer verification fails,
including query rewriting based on unsupported claims.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

from django.conf import settings

from .verifier import VerificationResult, AnswerVerifier
from .rewriter import QueryRewriter

logger = logging.getLogger(__name__)


@dataclass
class RetryResult:
    """
    Result of a retry attempt.

    Attributes:
        attempt_number: The retry attempt number (1-indexed).
        rewritten_query: The query used for this retry.
        retrieved_chunks: Chunks retrieved in this attempt.
        generated_answer: The answer generated in this attempt.
        verification_result: Verification result for this attempt.
        success: Whether this retry resulted in a verified answer.
        rewrite_strategy: Strategy used for query rewriting.
    """

    attempt_number: int
    rewritten_query: str
    retrieved_chunks: List[Any] = field(default_factory=list)
    generated_answer: str = ""
    verification_result: Optional[VerificationResult] = None
    success: bool = False
    rewrite_strategy: str = ""

    def to_dict(self) -> dict:
        """Convert the result to a dictionary."""
        return {
            'attempt_number': self.attempt_number,
            'rewritten_query': self.rewritten_query,
            'retrieved_chunk_count': len(self.retrieved_chunks),
            'generated_answer': self.generated_answer,
            'verification_result': (
                self.verification_result.to_dict()
                if self.verification_result else None
            ),
            'success': self.success,
            'rewrite_strategy': self.rewrite_strategy,
        }


class RetryError(Exception):
    """Raised when retry handling fails."""

    pass


class RetryHandler:
    """
    Handles retry logic for failed verifications.

    Triggers retries when:
    - grounded = False
    - faithfulness_score < threshold (default 0.7)

    Max retries: 2 by default

    The retry process:
    1. Rewrites the query based on unsupported claims
    2. Re-runs retrieval with the new query
    3. Re-generates the answer with new chunks
    4. Re-runs verification

    Attributes:
        faithfulness_threshold: Minimum faithfulness score to pass.
        max_retries: Maximum number of retry attempts.
    """

    DEFAULT_FAITHFULNESS_THRESHOLD: float = 0.7
    DEFAULT_MAX_RETRIES: int = 2

    def __init__(
        self,
        faithfulness_threshold: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initialize the retry handler.

        Args:
            faithfulness_threshold: Minimum faithfulness score.
                Defaults to settings.REASONING_FAITHFULNESS_THRESHOLD or 0.7.
            max_retries: Maximum number of retry attempts.
                Defaults to settings.REASONING_MAX_RETRIES or 2.
        """
        self.faithfulness_threshold = faithfulness_threshold or getattr(
            settings, 'REASONING_FAITHFULNESS_THRESHOLD',
            self.DEFAULT_FAITHFULNESS_THRESHOLD
        )
        self.max_retries = max_retries or getattr(
            settings, 'REASONING_MAX_RETRIES',
            self.DEFAULT_MAX_RETRIES
        )

        # Components for retry operations
        self._rewriter: Optional[QueryRewriter] = None
        self._verifier: Optional[AnswerVerifier] = None

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

    def should_retry(
        self,
        verification: VerificationResult,
        current_attempt: int,
    ) -> bool:
        """
        Determine if a retry should be attempted.

        Args:
            verification: The verification result.
            current_attempt: Current attempt number (1-indexed).

        Returns:
            True if retry should be attempted.
        """
        # Don't retry if we've hit the max
        if current_attempt >= self.max_retries + 1:  # +1 for initial attempt
            logger.info(
                f"Max retries ({self.max_retries}) reached, not retrying"
            )
            return False

        # Retry if not grounded
        if not verification.grounded:
            logger.info(
                f"Verification not grounded, retry #{current_attempt}"
            )
            return True

        # Retry if faithfulness score is below threshold
        if verification.faithfulness_score < self.faithfulness_threshold:
            logger.info(
                f"Faithfulness score {verification.faithfulness_score:.2f} "
                f"< threshold {self.faithfulness_threshold}, retry #{current_attempt}"
            )
            return True

        return False

    def handle(
        self,
        original_query: str,
        verification: VerificationResult,
        pipeline_name: str,
        subject_id: int,
        attempt_number: int,
        answer_generator_func: Any = None,
    ) -> RetryResult:
        """
        Handle a retry attempt.

        This method performs the query rewriting, but the actual retrieval
        and generation must be done by the caller (the ReasoningPipeline).

        Args:
            original_query: The original user query.
            verification: Failed verification result.
            pipeline_name: Retrieval pipeline to use.
            subject_id: Subject ID for retrieval.
            attempt_number: Current attempt number.
            answer_generator_func: Optional callback for generating answers.

        Returns:
            RetryResult with rewritten query (caller handles retrieval/generation).
        """
        logger.info(
            f"Handling retry attempt #{attempt_number} for query: "
            f"'{original_query[:50]}...'"
        )

        # Step 1: Rewrite query based on unsupported claims
        rewriter = self._get_rewriter()
        rewritten_query, strategy = rewriter.rewrite_for_retry(
            original_query=original_query,
            unsupported_claims=verification.unsupported_claims,
        )

        logger.info(
            f"Retry query rewritten: '{rewritten_query[:50]}...' "
            f"(Strategy: {strategy})"
        )

        # Return partial result - the pipeline will complete the retrieval
        # and generation steps
        return RetryResult(
            attempt_number=attempt_number,
            rewritten_query=rewritten_query,
            retrieved_chunks=[],  # Will be filled by pipeline
            generated_answer="",  # Will be filled by pipeline
            verification_result=None,  # Will be filled by pipeline
            success=False,  # Will be determined by pipeline
            rewrite_strategy=strategy,
        )

    def select_best_result(
        self,
        initial_answer: str,
        initial_verification: VerificationResult,
        retry_results: List[RetryResult],
    ) -> tuple[str, VerificationResult, bool]:
        """
        Select the best answer from all attempts.

        If no attempt passed verification, returns the answer with the
        highest faithfulness score.

        Args:
            initial_answer: The initial generated answer.
            initial_verification: Verification of initial answer.
            retry_results: List of retry attempt results.

        Returns:
            A tuple of (best_answer, best_verification, is_verified).
        """
        # Collect all attempts
        all_attempts = [
            (initial_answer, initial_verification)
        ]

        for retry in retry_results:
            if retry.verification_result is not None:
                all_attempts.append(
                    (retry.generated_answer, retry.verification_result)
                )

        # First, try to find a verified answer
        for answer, verification in all_attempts:
            if verification.grounded and verification.faithfulness_score >= self.faithfulness_threshold:
                logger.info(
                    f"Found verified answer with faithfulness "
                    f"{verification.faithfulness_score:.2f}"
                )
                return answer, verification, True

        # If no verified answer, return the one with highest faithfulness
        best_answer, best_verification = max(
            all_attempts,
            key=lambda x: x[1].faithfulness_score
        )

        logger.warning(
            f"No verified answer found, using best with faithfulness "
            f"{best_verification.faithfulness_score:.2f}"
        )

        return best_answer, best_verification, False

    def get_retry_info(self) -> Dict[str, Any]:
        """
        Get information about retry configuration.

        Returns:
            Dictionary with retry settings.
        """
        return {
            'faithfulness_threshold': self.faithfulness_threshold,
            'max_retries': self.max_retries,
        }
