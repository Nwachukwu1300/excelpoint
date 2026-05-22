"""
Query rewriting for improved retrieval.

Rewrites user queries to be more suitable for vector search,
incorporating conversation history when available.
"""

import json
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any

from openai import OpenAI
from django.conf import settings

from .prompts import (
    REWRITER_SYSTEM_PROMPT,
    REWRITER_USER_PROMPT_TEMPLATE,
    REWRITER_WITH_HISTORY_TEMPLATE,
)

logger = logging.getLogger(__name__)


@dataclass
class RewriteResult:
    """
    Result of query rewriting.

    Attributes:
        original_query: The original query before rewriting.
        rewritten_query: The rewritten query optimized for retrieval.
        changes_made: List of specific changes made to the query.
        latency_ms: Time taken for rewriting in milliseconds.
        raw_response: The raw LLM response string.
    """

    original_query: str
    rewritten_query: str
    changes_made: List[str]
    latency_ms: float
    raw_response: str

    def to_dict(self) -> dict:
        """Convert the result to a dictionary."""
        return {
            'original_query': self.original_query,
            'rewritten_query': self.rewritten_query,
            'changes_made': self.changes_made,
            'latency_ms': self.latency_ms,
            'raw_response': self.raw_response,
        }


class RewriteError(Exception):
    """Raised when query rewriting fails."""

    pass


class QueryRewriter:
    """
    Rewrites queries for better retrieval performance.

    Improves queries by:
    - Expanding abbreviations and acronyms
    - Adding relevant context from conversation history
    - Making implicit intent explicit
    - Removing conversational elements that don't aid retrieval

    Attributes:
        model: The OpenAI model to use for rewriting.
        temperature: LLM temperature for rewriting calls.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the rewriter.

        Args:
            model: OpenAI model to use. Defaults to settings.REASONING_LLM_MODEL
                   or settings.OPENAI_MODEL.
            temperature: LLM temperature for rewriting. Defaults to
                        settings.REASONING_REWRITER_TEMPERATURE or 0.3.
        """
        self._model = model or getattr(
            settings, 'REASONING_LLM_MODEL',
            getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        )
        self._temperature = temperature if temperature is not None else getattr(
            settings, 'REASONING_REWRITER_TEMPERATURE', 0.3
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

    def rewrite(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> RewriteResult:
        """
        Rewrite a query for improved retrieval.

        Args:
            query: The original query to rewrite.
            conversation_history: Previous conversation exchanges.
                Each dict should have 'role' and 'content' keys.

        Returns:
            RewriteResult with rewritten query and changes.
        """
        if not query or not query.strip():
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                changes_made=[],
                latency_ms=0.0,
                raw_response="",
            )

        query = query.strip()
        start_time = time.perf_counter()

        try:
            client = self._get_client()

            # Build the user prompt based on whether history is provided
            if conversation_history and len(conversation_history) > 0:
                history_str = self._format_conversation_history(conversation_history)
                user_prompt = REWRITER_WITH_HISTORY_TEMPLATE.format(
                    conversation_history=history_str,
                    query=query,
                )
            else:
                user_prompt = REWRITER_USER_PROMPT_TEMPLATE.format(query=query)

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": REWRITER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._temperature,
                max_tokens=500,
            )

            raw_response = response.choices[0].message.content or ""
            latency_ms = (time.perf_counter() - start_time) * 1000

            rewritten_query, changes_made = self._parse_rewrite_response(
                raw_response, query
            )

            logger.info(
                f"Rewrote query: '{query[:30]}...' -> '{rewritten_query[:30]}...'"
            )

            return RewriteResult(
                original_query=query,
                rewritten_query=rewritten_query,
                changes_made=changes_made,
                latency_ms=latency_ms,
                raw_response=raw_response,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                f"Query rewriting failed, using original query: {str(e)}"
            )
            # Fallback to original query on failure
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                changes_made=[],
                latency_ms=latency_ms,
                raw_response=f"Error: {str(e)}",
            )

    def _format_conversation_history(
        self, history: List[Dict[str, str]]
    ) -> str:
        """
        Format conversation history for the prompt.

        Args:
            history: List of conversation exchanges.

        Returns:
            Formatted string representation of the history.
        """
        formatted_lines = []
        for i, exchange in enumerate(history[-5:], 1):  # Limit to last 5 exchanges
            role = exchange.get('role', 'unknown').capitalize()
            content = exchange.get('content', '')
            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."
            formatted_lines.append(f"{role}: {content}")
        return "\n".join(formatted_lines)

    def _parse_rewrite_response(
        self, response: str, original_query: str
    ) -> Tuple[str, List[str]]:
        """
        Parse LLM response into rewritten query and changes list.

        Args:
            response: The raw LLM response string.
            original_query: The original query (for fallback).

        Returns:
            A tuple of (rewritten_query, changes_made).
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

            rewritten_query = data.get("rewritten_query", original_query)
            changes_made = data.get("changes_made", [])

            # Ensure changes_made is a list
            if not isinstance(changes_made, list):
                changes_made = [str(changes_made)] if changes_made else []

            # Validate rewritten query is not empty
            if not rewritten_query or not rewritten_query.strip():
                rewritten_query = original_query
                changes_made = []

            return rewritten_query.strip(), changes_made

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse rewrite JSON: {response[:100]}...")
            # Fallback to original query
            return original_query, []
        except Exception as e:
            logger.warning(f"Error parsing rewrite response: {str(e)}")
            return original_query, []

    def rewrite_for_retry(
        self,
        original_query: str,
        unsupported_claims: List[str],
    ) -> Tuple[str, str]:
        """
        Rewrite query specifically for retry attempts.

        This method creates a more targeted query based on unsupported
        claims from a previous verification failure.

        Args:
            original_query: The original query.
            unsupported_claims: List of claims that were not supported.

        Returns:
            A tuple of (rewritten_query, strategy).
        """
        from .prompts import (
            RETRY_REWRITER_SYSTEM_PROMPT,
            RETRY_REWRITER_USER_PROMPT_TEMPLATE,
        )

        if not unsupported_claims:
            return original_query, "No unsupported claims to target"

        start_time = time.perf_counter()

        try:
            client = self._get_client()

            claims_str = "\n".join(f"- {claim}" for claim in unsupported_claims[:5])
            user_prompt = RETRY_REWRITER_USER_PROMPT_TEMPLATE.format(
                original_query=original_query,
                unsupported_claims=claims_str,
            )

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": RETRY_REWRITER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._temperature,
                max_tokens=300,
            )

            raw_response = response.choices[0].message.content or ""

            # Parse response
            try:
                cleaned_response = raw_response.strip()
                if cleaned_response.startswith("```"):
                    lines = cleaned_response.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    cleaned_response = "\n".join(lines)

                data = json.loads(cleaned_response)
                rewritten_query = data.get("rewritten_query", original_query)
                strategy = data.get("strategy", "LLM-based refinement")

                logger.info(
                    f"Retry rewrite: '{original_query[:30]}...' -> "
                    f"'{rewritten_query[:30]}...' (Strategy: {strategy})"
                )

                return rewritten_query, strategy

            except json.JSONDecodeError:
                logger.warning("Failed to parse retry rewrite JSON")
                return original_query, "JSON parsing failed"

        except Exception as e:
            logger.warning(f"Retry rewriting failed: {str(e)}")
            return original_query, f"Error: {str(e)}"
