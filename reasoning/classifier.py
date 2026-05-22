"""
Query classification for the reasoning pipeline.

Classifies queries into categories to determine the appropriate
processing path: direct response, retrieval required, or clarification needed.
"""

import json
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple

from openai import OpenAI
from django.conf import settings

from .prompts import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class QueryClassificationCategory(Enum):
    """
    Categories for query classification.

    DIRECT_RESPONSE: Query can be answered without retrieval.
    RETRIEVAL_REQUIRED: Query needs document retrieval.
    CLARIFICATION_REQUIRED: Query is too vague and needs clarification.
    """

    DIRECT_RESPONSE = "direct_response"
    RETRIEVAL_REQUIRED = "retrieval_required"
    CLARIFICATION_REQUIRED = "clarification_required"

    @classmethod
    def from_string(cls, value: str) -> 'QueryClassificationCategory':
        """
        Convert a string to a QueryClassificationCategory.

        Args:
            value: The string value to convert.

        Returns:
            The corresponding QueryClassificationCategory.

        Raises:
            ValueError: If the value is not a valid category.
        """
        value_lower = value.lower().strip()
        for category in cls:
            if category.value == value_lower:
                return category
        raise ValueError(f"Invalid classification category: {value}")


@dataclass
class ClassificationResult:
    """
    Result of query classification.

    Attributes:
        original_query: The original query that was classified.
        category: The assigned classification category.
        reasoning: Explanation for the classification decision.
        latency_ms: Time taken for classification in milliseconds.
        raw_response: The raw LLM response string.
    """

    original_query: str
    category: QueryClassificationCategory
    reasoning: str
    latency_ms: float
    raw_response: str

    def to_dict(self) -> dict:
        """Convert the result to a dictionary."""
        return {
            'original_query': self.original_query,
            'category': self.category.value,
            'reasoning': self.reasoning,
            'latency_ms': self.latency_ms,
            'raw_response': self.raw_response,
        }


class ClassificationError(Exception):
    """Raised when query classification fails."""

    pass


class QueryClassifier:
    """
    Classifies incoming queries to determine processing path.

    Uses LLM to analyze query intent and classify into appropriate category:
    - DIRECT_RESPONSE: Can be answered without retrieval
    - RETRIEVAL_REQUIRED: Needs document retrieval
    - CLARIFICATION_REQUIRED: Query is too vague

    Attributes:
        model: The OpenAI model to use for classification.
        temperature: LLM temperature for classification calls.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the classifier.

        Args:
            model: OpenAI model to use. Defaults to settings.REASONING_LLM_MODEL
                   or settings.OPENAI_MODEL.
            temperature: LLM temperature for classification. Defaults to
                        settings.REASONING_CLASSIFIER_TEMPERATURE or 0.2.
        """
        self._model = model or getattr(
            settings, 'REASONING_LLM_MODEL',
            getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        )
        self._temperature = temperature if temperature is not None else getattr(
            settings, 'REASONING_CLASSIFIER_TEMPERATURE', 0.2
        )
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        """
        Get or create the OpenAI client.

        Returns:
            The OpenAI client instance.
        """
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def classify(self, query: str) -> ClassificationResult:
        """
        Classify a query into a category.

        Args:
            query: The user's query to classify.

        Returns:
            ClassificationResult with category and reasoning.

        Raises:
            ClassificationError: If classification fails.
        """
        if not query or not query.strip():
            raise ClassificationError("Query cannot be empty")

        query = query.strip()
        start_time = time.perf_counter()

        try:
            client = self._get_client()
            user_prompt = CLASSIFIER_USER_PROMPT_TEMPLATE.format(query=query)

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._temperature,
                max_tokens=200,
            )

            raw_response = response.choices[0].message.content or ""
            latency_ms = (time.perf_counter() - start_time) * 1000

            category, reasoning = self._parse_classification_response(raw_response)

            logger.info(
                f"Classified query as {category.value}: {query[:50]}..."
            )

            return ClassificationResult(
                original_query=query,
                category=category,
                reasoning=reasoning,
                latency_ms=latency_ms,
                raw_response=raw_response,
            )

        except ClassificationError:
            raise
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Classification failed: {str(e)}")
            raise ClassificationError(f"Failed to classify query: {str(e)}")

    def _parse_classification_response(
        self, response: str
    ) -> Tuple[QueryClassificationCategory, str]:
        """
        Parse LLM response into category and reasoning.

        Args:
            response: The raw LLM response string.

        Returns:
            A tuple of (category, reasoning).

        Raises:
            ClassificationError: If the response cannot be parsed.
        """
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```"):
                # Remove markdown code block markers
                lines = cleaned_response.split("\n")
                # Remove first and last lines if they are code block markers
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_response = "\n".join(lines)

            data = json.loads(cleaned_response)

            category_str = data.get("category", "").upper().replace(" ", "_")
            reasoning = data.get("reasoning", "No reasoning provided")

            # Normalize category string
            if category_str == "DIRECT_RESPONSE":
                category = QueryClassificationCategory.DIRECT_RESPONSE
            elif category_str == "RETRIEVAL_REQUIRED":
                category = QueryClassificationCategory.RETRIEVAL_REQUIRED
            elif category_str == "CLARIFICATION_REQUIRED":
                category = QueryClassificationCategory.CLARIFICATION_REQUIRED
            else:
                # Try to match by value
                category = QueryClassificationCategory.from_string(category_str)

            return category, reasoning

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse classification JSON: {response}")
            # Attempt fallback parsing
            response_lower = response.lower()
            if "direct_response" in response_lower:
                return (
                    QueryClassificationCategory.DIRECT_RESPONSE,
                    "Parsed from non-JSON response",
                )
            elif "retrieval_required" in response_lower:
                return (
                    QueryClassificationCategory.RETRIEVAL_REQUIRED,
                    "Parsed from non-JSON response",
                )
            elif "clarification_required" in response_lower:
                return (
                    QueryClassificationCategory.CLARIFICATION_REQUIRED,
                    "Parsed from non-JSON response",
                )
            raise ClassificationError(
                f"Failed to parse classification response: {str(e)}"
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Invalid classification response structure: {response}")
            raise ClassificationError(
                f"Invalid classification response structure: {str(e)}"
            )
