"""
WikipediaTool — implements AbstractTool. Multi-hop by design:

Hop 1 (entity resolution): resolve the topic to an actual Wikipedia page.
Hop 2 (fact extraction): given the full page content and the user's
ORIGINAL question, ask Gemini to extract the specific answer — not just
return the intro paragraph.
"""

from typing import Any

import wikipediaapi

from core.contracts import ToolName, ToolResult
from llm.client import GeminiClient, LLMError
from llm.prompts import WIKI_FACT_EXTRACTION_PROMPT
from resilience.fallback import FallbackChain
from resilience.retry import retry_with_backoff
from tools.base import AbstractTool
from utils.logger import get_logger

logger = get_logger(__name__)

_wiki_client = wikipediaapi.Wikipedia(user_agent="AI-Agent-Project/1.0", language="en")


class WikipediaAPIError(Exception):
    pass


class WikipediaTool(AbstractTool):
    name = ToolName.WIKIPEDIA

    def __init__(self, llm_client: GeminiClient):
        self._llm_client = llm_client

    def execute(self, params: dict[str, Any], request_id: str) -> ToolResult:
        topic = params.get("topic", "")
        question = params.get("question", topic)

        if not topic:
            return ToolResult(
                request_id=request_id, tool_name=self.name, success=False,
                error_message="No topic provided",
            )

        chain = FallbackChain([
            lambda: self._lookup_and_extract(topic, question, request_id),
            lambda: self._graceful_degradation(topic, request_id),
        ])
        return chain.run(request_id=request_id, tool_name=self.name)

    @retry_with_backoff(max_attempts=3, base_delay_seconds=1.0, retryable_exceptions=(WikipediaAPIError,))
    def _lookup_and_extract(self, topic: str, question: str, request_id: str) -> ToolResult:
        try:
            page = _wiki_client.page(topic)
            if not page.exists():
                logger.info(f"[{request_id}] No Wikipedia page found for '{topic}'")
                return ToolResult(
                    request_id=request_id, tool_name=self.name, success=True,
                    data={"topic": topic, "message": f"I couldn't find a Wikipedia page for '{topic}'."},
                )
            page_content = page.summary[:2000]  # cap length for prompt size
        except Exception as e:
            logger.error(f"[{request_id}] Wikipedia lookup failed: {e}")
            raise WikipediaAPIError(f"Wikipedia request failed: {e}") from e

        try:
            answer = self._extract_fact(question, page_content, request_id)
        except LLMError as e:
            logger.warning(f"[{request_id}] Fact extraction failed, falling back to raw summary: {e}")
            answer = page_content

        logger.info(f"[{request_id}] Wikipedia multi-hop resolved for '{topic}'")
        return ToolResult(
            request_id=request_id, tool_name=self.name, success=True,
            data={"topic": topic, "summary": answer},
        )

    def _extract_fact(self, question: str, page_content: str, request_id: str) -> str:
        prompt = WIKI_FACT_EXTRACTION_PROMPT.format(question=question, content=page_content)
        return self._llm_client.generate(prompt)

    def _graceful_degradation(self, topic: str, request_id: str) -> ToolResult:
        logger.warning(f"[{request_id}] Wikipedia unavailable for '{topic}', degrading gracefully")
        return ToolResult(
            request_id=request_id, tool_name=self.name, success=True,
            data={"topic": topic, "message": f"Information about '{topic}' is temporarily unavailable. Please try again shortly."},
        )