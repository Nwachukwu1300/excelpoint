"""
Answer verification against source chunks.

Verifies that generated answers are grounded in the retrieved content
and identifies supported vs unsupported claims.
"""

import json
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

from openai import OpenAI
from django.conf import settings

from .prompts import VERIFIER_SYSTEM_PROMPT, VERIFIER_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """
    Result of answer verification.

    Attributes:
        grounded: Whether the answer is considered grounded in the sources.
        supported_claims: List of claims that ARE supported by the sources.
        unsupported_claims: List of claims that are NOT supported by the sources.
        faithfulness_score: Overall faithfulness score (0.0 to 1.0).
        reasoning: Explanation of the verification assessment.
        latency_ms: Time taken for verification in milliseconds.
        raw_response: The raw LLM response string.
    """

    grounded: bool
    supported_claims: List[str] = field(default_factory=list)
    unsupported_claims: List[str] = field(default_factory=list)
    faithfulness_score: float = 0.0
    reasoning: str = ""
    latency_ms: float = 0.0
    raw_response: str = ""

    def to_dict(self) -> dict:
        """Convert the result to a dictionary."""
        return {
            'grounded': self.grounded,
            'supported_claims': self.supported_claims,
            'unsupported_claims': self.unsupported_claims,
            'faithfulness_score': self.faithfulness_score,
            'reasoning': self.reasoning,
            'latency_ms': self.latency_ms,
            'raw_response': self.raw_response,
        }


class VerificationError(Exception):
    """Raised when answer verification fails."""

    pass


class AnswerVerifier:
    """
    Verifies answers against source content.

    Analyzes whether claims in an answer are supported by
    the retrieved chunks, identifying both supported and
    unsupported claims.

    Attributes:
        model: The OpenAI model to use for verification.
        temperature: LLM temperature for verification calls.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the verifier.

        Args:
            model: OpenAI model to use. Defaults to settings.REASONING_LLM_MODEL
                   or settings.OPENAI_MODEL.
            temperature: LLM temperature for verification (low for consistency).
                        Defaults to settings.REASONING_VERIFIER_TEMPERATURE or 0.1.
        """
        self._model = model or getattr(
            settings, 'REASONING_LLM_MODEL',
            getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        )
        self._temperature = temperature if temperature is not None else getattr(
            settings, 'REASONING_VERIFIER_TEMPERATURE', 0.1
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

    def verify(
        self,
        answer: str,
        chunks: List[Any],
    ) -> VerificationResult:
        """
        Verify an answer against source chunks.

        Args:
            answer: The generated answer to verify.
            chunks: Retrieved chunks used to generate the answer.
                   Can be RankedChunk objects or dicts with 'content' key.

        Returns:
            VerificationResult with grounding assessment.

        Raises:
            VerificationError: If verification fails critically.
        """
        if not answer or not answer.strip():
            return VerificationResult(
                grounded=False,
                supported_claims=[],
                unsupported_claims=["Empty answer provided"],
                faithfulness_score=0.0,
                reasoning="Cannot verify empty answer",
                latency_ms=0.0,
                raw_response="",
            )

        if not chunks:
            return VerificationResult(
                grounded=False,
                supported_claims=[],
                unsupported_claims=["No source chunks provided for verification"],
                faithfulness_score=0.0,
                reasoning="Cannot verify answer without source content",
                latency_ms=0.0,
                raw_response="",
            )

        start_time = time.perf_counter()

        try:
            client = self._get_client()

            # Format chunks for the prompt
            context = self._format_chunks_for_verification(chunks)

            user_prompt = VERIFIER_USER_PROMPT_TEMPLATE.format(
                context=context,
                answer=answer,
            )

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._temperature,
                max_tokens=1000,
            )

            raw_response = response.choices[0].message.content or ""
            latency_ms = (time.perf_counter() - start_time) * 1000

            result = self._parse_verification_response(raw_response)
            result.latency_ms = latency_ms
            result.raw_response = raw_response

            logger.info(
                f"Verification complete: grounded={result.grounded}, "
                f"faithfulness={result.faithfulness_score:.2f}, "
                f"supported={len(result.supported_claims)}, "
                f"unsupported={len(result.unsupported_claims)}"
            )

            return result

        except VerificationError:
            raise
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Verification failed: {str(e)}")
            # Return a conservative result on failure
            return VerificationResult(
                grounded=False,
                supported_claims=[],
                unsupported_claims=["Verification failed due to error"],
                faithfulness_score=0.5,
                reasoning=f"Verification process failed: {str(e)}",
                latency_ms=latency_ms,
                raw_response=f"Error: {str(e)}",
            )

    def _format_chunks_for_verification(self, chunks: List[Any]) -> str:
        """
        Format chunks into a string for the verification prompt.

        Args:
            chunks: List of chunk objects or dicts.

        Returns:
            Formatted string representation of chunks.
        """
        formatted_chunks = []

        for i, chunk in enumerate(chunks[:10], 1):  # Limit to 10 chunks
            # Handle both RankedChunk objects and dicts
            if hasattr(chunk, 'content'):
                content = chunk.content
                material_name = getattr(chunk, 'material_name', 'Unknown')
            elif isinstance(chunk, dict):
                content = chunk.get('content', str(chunk))
                material_name = chunk.get('material_name', 'Unknown')
            else:
                content = str(chunk)
                material_name = 'Unknown'

            # Truncate very long chunks
            if len(content) > 1500:
                content = content[:1500] + "..."

            formatted_chunks.append(
                f"[Chunk {i} - Source: {material_name}]\n{content}"
            )

        return "\n\n---\n\n".join(formatted_chunks)

    def _parse_verification_response(self, response: str) -> VerificationResult:
        """
        Parse LLM response into verification components.

        Args:
            response: The raw LLM response string.

        Returns:
            VerificationResult with parsed data.
        """
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```"):
                lines = cleaned_response.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_response = "\n".join(lines)

            data = json.loads(cleaned_response)

            grounded = bool(data.get("grounded", False))
            supported_claims = data.get("supported_claims", [])
            unsupported_claims = data.get("unsupported_claims", [])
            faithfulness_score = float(data.get("faithfulness_score", 0.0))
            reasoning = data.get("reasoning", "No reasoning provided")

            # Ensure lists are actually lists
            if not isinstance(supported_claims, list):
                supported_claims = [str(supported_claims)] if supported_claims else []
            if not isinstance(unsupported_claims, list):
                unsupported_claims = [str(unsupported_claims)] if unsupported_claims else []

            # Clamp faithfulness score to [0, 1]
            faithfulness_score = max(0.0, min(1.0, faithfulness_score))

            return VerificationResult(
                grounded=grounded,
                supported_claims=supported_claims,
                unsupported_claims=unsupported_claims,
                faithfulness_score=faithfulness_score,
                reasoning=reasoning,
            )

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse verification JSON: {response[:200]}...")
            # Attempt to extract some information from non-JSON response
            response_lower = response.lower()
            grounded = "grounded" in response_lower and "not grounded" not in response_lower
            return VerificationResult(
                grounded=grounded,
                supported_claims=[],
                unsupported_claims=["Unable to parse verification details"],
                faithfulness_score=0.5 if grounded else 0.3,
                reasoning="Parsed from non-JSON response",
            )
        except Exception as e:
            logger.warning(f"Error parsing verification response: {str(e)}")
            return VerificationResult(
                grounded=False,
                supported_claims=[],
                unsupported_claims=["Error parsing verification"],
                faithfulness_score=0.3,
                reasoning=f"Parse error: {str(e)}",
            )
