"""
Thin wrapper around the Gemini API. Knows nothing about tools or pipeline stages —
just takes a prompt, returns a response. Kept isolated so the LLM provider is swappable.
"""

from google import genai
from google.genai import types
from resilience.retry import retry_with_backoff
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMError(Exception):
    """Raised when the Gemini API call fails for any reason.
    Narrow, specific exception type — callers can catch this without
    accidentally swallowing unrelated bugs."""
    pass


class GeminiClient:
    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model_name = settings.gemini_model_name

    @retry_with_backoff(max_attempts=4, base_delay_seconds=2.0, retryable_exceptions=(LLMError,))
    
    def generate(self, prompt: str) -> str:
        """Send a prompt to Gemini, return the raw text response.

        Raises LLMError on any failure — timeout, rate limit, empty response, etc.
        Retry/fallback policy is NOT handled here; that's resilience/retry.py's job.
        """
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=1024,
                ),
            )
            if not response.text:
                raise LLMError("Gemini returned an empty response")
            logger.info(f"Gemini call succeeded, response length={len(response.text)}")
            return response.text
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            raise LLMError(f"Gemini API call failed: {e}") from e