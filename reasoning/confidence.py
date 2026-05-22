"""
Confidence scoring for reasoning results.

Calculates confidence scores based on verification results,
retrieval quality, and other factors.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from django.conf import settings

from .verifier import VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    """
    Confidence score with breakdown.

    Attributes:
        final_score: The final computed confidence score (0.0 to 1.0).
        score_breakdown: Dictionary showing each component and its contribution.
        interpretation: Human-readable interpretation (HIGH/MODERATE/LOW).
    """

    final_score: float
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    interpretation: str = ""

    def to_dict(self) -> dict:
        """Convert the score to a dictionary."""
        return {
            'final_score': self.final_score,
            'score_breakdown': self.score_breakdown,
            'interpretation': self.interpretation,
        }


class ConfidenceScorer:
    """
    Calculates confidence scores for reasoning results.

    Uses a weighted formula combining multiple factors:
    - Faithfulness score (40%)
    - Mean similarity score (25%)
    - Top similarity score (15%)
    - First attempt bonus (10%)
    - Unsupported claim penalty (5% each, max 20%)

    The final score is normalized to a value between 0 and 1.

    Attributes:
        faithfulness_weight: Weight for faithfulness score component.
        mean_similarity_weight: Weight for mean similarity score.
        top_similarity_weight: Weight for top similarity score.
        first_attempt_bonus: Bonus for successful first attempt.
        unsupported_claim_penalty: Penalty per unsupported claim.
        max_unsupported_penalty: Maximum total penalty for unsupported claims.
    """

    # Default weights (can be overridden via settings or constructor)
    DEFAULT_FAITHFULNESS_WEIGHT: float = 0.40
    DEFAULT_MEAN_SIMILARITY_WEIGHT: float = 0.25
    DEFAULT_TOP_SIMILARITY_WEIGHT: float = 0.15
    DEFAULT_FIRST_ATTEMPT_BONUS: float = 0.10
    DEFAULT_UNSUPPORTED_CLAIM_PENALTY: float = 0.05
    DEFAULT_MAX_UNSUPPORTED_PENALTY: float = 0.20

    # Interpretation thresholds
    HIGH_THRESHOLD: float = 0.80
    MODERATE_THRESHOLD: float = 0.50

    def __init__(
        self,
        faithfulness_weight: Optional[float] = None,
        mean_similarity_weight: Optional[float] = None,
        top_similarity_weight: Optional[float] = None,
        first_attempt_bonus: Optional[float] = None,
        unsupported_claim_penalty: Optional[float] = None,
        max_unsupported_penalty: Optional[float] = None,
    ):
        """
        Initialize the scorer with optional custom weights.

        Args:
            faithfulness_weight: Weight for faithfulness score.
            mean_similarity_weight: Weight for mean chunk similarity.
            top_similarity_weight: Weight for top chunk similarity.
            first_attempt_bonus: Bonus for successful first attempt.
            unsupported_claim_penalty: Penalty per unsupported claim.
            max_unsupported_penalty: Maximum penalty for unsupported claims.
        """
        # Load from settings or use defaults
        self.faithfulness_weight = faithfulness_weight or getattr(
            settings, 'REASONING_CONFIDENCE_FAITHFULNESS_WEIGHT',
            self.DEFAULT_FAITHFULNESS_WEIGHT
        )
        self.mean_similarity_weight = mean_similarity_weight or getattr(
            settings, 'REASONING_CONFIDENCE_MEAN_SIMILARITY_WEIGHT',
            self.DEFAULT_MEAN_SIMILARITY_WEIGHT
        )
        self.top_similarity_weight = top_similarity_weight or getattr(
            settings, 'REASONING_CONFIDENCE_TOP_SIMILARITY_WEIGHT',
            self.DEFAULT_TOP_SIMILARITY_WEIGHT
        )
        self.first_attempt_bonus = first_attempt_bonus or getattr(
            settings, 'REASONING_CONFIDENCE_FIRST_ATTEMPT_BONUS',
            self.DEFAULT_FIRST_ATTEMPT_BONUS
        )
        self.unsupported_claim_penalty = unsupported_claim_penalty or getattr(
            settings, 'REASONING_CONFIDENCE_UNSUPPORTED_PENALTY',
            self.DEFAULT_UNSUPPORTED_CLAIM_PENALTY
        )
        self.max_unsupported_penalty = max_unsupported_penalty or getattr(
            settings, 'REASONING_CONFIDENCE_MAX_UNSUPPORTED_PENALTY',
            self.DEFAULT_MAX_UNSUPPORTED_PENALTY
        )

    def score(
        self,
        verification: VerificationResult,
        chunks: List[Any],
        is_first_attempt: bool = True,
    ) -> ConfidenceScore:
        """
        Calculate confidence score for a reasoning result.

        Args:
            verification: The verification result.
            chunks: Retrieved chunks used in generation.
            is_first_attempt: Whether this was the first attempt.

        Returns:
            ConfidenceScore with breakdown and interpretation.
        """
        score_breakdown: Dict[str, float] = {}

        # Component 1: Faithfulness score (40%)
        faithfulness_contribution = (
            verification.faithfulness_score * self.faithfulness_weight
        )
        score_breakdown['faithfulness'] = faithfulness_contribution

        # Component 2 & 3: Similarity scores (25% + 15%)
        mean_similarity, top_similarity = self._calculate_similarity_scores(chunks)

        mean_similarity_contribution = mean_similarity * self.mean_similarity_weight
        top_similarity_contribution = top_similarity * self.top_similarity_weight

        score_breakdown['mean_similarity'] = mean_similarity_contribution
        score_breakdown['top_similarity'] = top_similarity_contribution

        # Component 4: First attempt bonus (10%)
        first_attempt_contribution = self.first_attempt_bonus if is_first_attempt else 0.0
        score_breakdown['first_attempt_bonus'] = first_attempt_contribution

        # Component 5: Unsupported claim penalty (-5% each, max -20%)
        num_unsupported = len(verification.unsupported_claims)
        unsupported_penalty = min(
            num_unsupported * self.unsupported_claim_penalty,
            self.max_unsupported_penalty
        )
        score_breakdown['unsupported_penalty'] = -unsupported_penalty

        # Calculate raw score
        raw_score = (
            faithfulness_contribution +
            mean_similarity_contribution +
            top_similarity_contribution +
            first_attempt_contribution -
            unsupported_penalty
        )

        # Normalize to [0, 1]
        final_score = max(0.0, min(1.0, raw_score))

        # Get interpretation
        interpretation = self._interpret_score(final_score)

        logger.debug(
            f"Confidence score: {final_score:.3f} ({interpretation}) - "
            f"breakdown: {score_breakdown}"
        )

        return ConfidenceScore(
            final_score=final_score,
            score_breakdown=score_breakdown,
            interpretation=interpretation,
        )

    def _calculate_similarity_scores(
        self, chunks: List[Any]
    ) -> tuple[float, float]:
        """
        Calculate mean and top similarity scores from chunks.

        Args:
            chunks: List of chunk objects.

        Returns:
            A tuple of (mean_score, top_score).
        """
        if not chunks:
            return 0.0, 0.0

        scores = []
        for chunk in chunks:
            # Try to get the best available score (reranked or initial)
            if hasattr(chunk, 'reranked_score') and chunk.reranked_score is not None:
                scores.append(chunk.reranked_score)
            elif hasattr(chunk, 'initial_score'):
                scores.append(chunk.initial_score)
            elif isinstance(chunk, dict):
                score = chunk.get('reranked_score') or chunk.get('initial_score') or chunk.get('similarity_score', 0.0)
                scores.append(score)

        if not scores:
            return 0.0, 0.0

        mean_score = sum(scores) / len(scores)
        top_score = max(scores)

        return mean_score, top_score

    def _interpret_score(self, score: float) -> str:
        """
        Interpret numerical score as HIGH/MODERATE/LOW.

        Args:
            score: The confidence score (0.0 to 1.0).

        Returns:
            Interpretation string.
        """
        if score >= self.HIGH_THRESHOLD:
            return "HIGH_CONFIDENCE"
        elif score >= self.MODERATE_THRESHOLD:
            return "MODERATE_CONFIDENCE"
        else:
            return "LOW_CONFIDENCE"

    def get_weights_info(self) -> Dict[str, float]:
        """
        Get information about the current weight configuration.

        Returns:
            Dictionary of weight names and values.
        """
        return {
            'faithfulness_weight': self.faithfulness_weight,
            'mean_similarity_weight': self.mean_similarity_weight,
            'top_similarity_weight': self.top_similarity_weight,
            'first_attempt_bonus': self.first_attempt_bonus,
            'unsupported_claim_penalty': self.unsupported_claim_penalty,
            'max_unsupported_penalty': self.max_unsupported_penalty,
        }
