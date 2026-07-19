"""
Stage 5: Response Generation.
Takes a validated result, produces the final natural-language answer via Gemini.
Separate LLM call from Intent Understanding — different responsibility, different prompt.

Deliberately does NOT call Gemini when validation failed — a failure message
is constructed directly, since an LLM call adds cost/latency/a new failure
point for something a plain string template already handles correctly.
"""

from core.contracts import AgentResponse, IntentType, ToolName, ValidatedResult
from llm.client import GeminiClient, LLMError
from llm.prompts import RESPONSE_GENERATION_PROMPT
from utils.logger import get_logger

logger = get_logger(__name__)


class Responder:
    def __init__(self, llm_client: GeminiClient):
        self._llm_client = llm_client

    def respond(self, validated: ValidatedResult, intent_type: IntentType) -> AgentResponse:
        if not validated.is_valid:
            return self._build_failure_response(validated, intent_type)

        try:
            answer = self._generate_natural_answer(validated)
        except LLMError as e:
            # Response generation itself failing is NOT the same as tool
            # failure — we already HAVE valid data, we just couldn't phrase
            # it nicely. Fall back to a plain, deterministic rendering of
            # the raw data rather than losing the answer entirely.
            logger.warning(f"[{validated.request_id}] Response phrasing failed, using raw data fallback: {e}")
            answer = self._raw_data_fallback(validated)

        return AgentResponse(
            request_id=validated.request_id,
            answer=answer,
            success=True,
            intent_type=intent_type,
            tool_used=validated.tool_name,
            used_fallback=False,
        )

    def respond_unknown_intent(self, request_id: str) -> AgentResponse:
        """No tool was run at all — the intent itself couldn't be classified."""
        return AgentResponse(
            request_id=request_id,
            answer="I'm not sure what you're asking. Could you rephrase that?",
            success=False,
            intent_type=IntentType.UNKNOWN,
            tool_used=ToolName.NONE,
            used_fallback=False,
        )

    def _generate_natural_answer(self, validated: ValidatedResult) -> str:
        prompt = RESPONSE_GENERATION_PROMPT.format(
            tool_name=validated.tool_name.value,
            data=validated.data,
        )
        return self._llm_client.generate(prompt)

    def _raw_data_fallback(self, validated: ValidatedResult) -> str:
        """Plain, deterministic rendering when Gemini phrasing fails but data is valid."""
        return f"Here's what I found: {validated.data}"

    def _build_failure_response(self, validated: ValidatedResult, intent_type: IntentType) -> AgentResponse:
        return AgentResponse(
            request_id=validated.request_id,
            answer=f"I couldn't get a reliable answer for that ({validated.validation_notes}). Please try again.",
            success=False,
            intent_type=intent_type,
            tool_used=validated.tool_name,
            used_fallback=False,
        )