"""
Stage 1: Intent Understanding.
Takes the raw user query, returns a structured Intent (what does the user want?).
Does NOT decide which tool to use — that's Planning's job.
"""

import json

from pydantic import ValidationError

from core.contracts import AgentRequest, Intent, IntentType
from llm.client import GeminiClient, LLMError
from llm.prompts import INTENT_UNDERSTANDING_PROMPT
from utils.logger import get_logger

logger = get_logger(__name__)


class IntentUnderstandingError(Exception):
    """Raised when intent cannot be determined, even after fallback to UNKNOWN."""
    pass


class IntentUnderstander:
    def __init__(self, llm_client: GeminiClient):
        self._llm_client = llm_client

    def understand(self, request: AgentRequest) -> Intent:
        """Classify the user's query into a structured Intent.

        Never raises for a genuinely ambiguous query — falls back to
        IntentType.UNKNOWN with low confidence rather than crashing the
        pipeline. Only raises IntentUnderstandingError if the LLM call
        itself fails after retries (infrastructure failure, not ambiguity).
        """
        prompt = INTENT_UNDERSTANDING_PROMPT.format(query=request.query)

        try:
            raw_response = self._llm_client.generate(prompt)
        except LLMError as e:
            logger.error(f"[{request.request_id}] LLM call failed during intent understanding: {e}")
            raise IntentUnderstandingError(f"Could not reach LLM: {e}") from e

        parsed = self._parse_llm_response(raw_response, request.request_id)

        try:
            intent = Intent(
                request_id=request.request_id,
                intent_type=IntentType(parsed.get("intent_type", "unknown")),
                raw_query=request.query,
                extracted_entities=parsed.get("extracted_entities", {}),
                confidence=float(parsed.get("confidence", 0.0)),
            )
        except (ValidationError, ValueError) as e:
            # LLM returned something that doesn't match our contract.
            # Fail gracefully into UNKNOWN rather than crashing the pipeline.
            logger.warning(f"[{request.request_id}] LLM response failed validation: {e}. Falling back to UNKNOWN.")
            intent = Intent(
                request_id=request.request_id,
                intent_type=IntentType.UNKNOWN,
                raw_query=request.query,
                extracted_entities={},
                confidence=0.0,
            )

        logger.info(f"[{request.request_id}] Intent classified: {intent.intent_type.value} (confidence={intent.confidence})")
        return intent

    def _parse_llm_response(self, raw_response: str, request_id: str) -> dict:
        """Defensively parse the LLM's JSON response. Strips markdown fences
        if present (Gemini sometimes wraps JSON in ```json ... ``` despite
        instructions not to)."""
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"[{request_id}] Could not parse LLM response as JSON: {e}. Raw: {raw_response[:200]}")
            return {}