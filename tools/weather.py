"""
WeatherTool — implements AbstractTool. Wraps OpenWeather API, uses
retry_with_backoff for transient failures and FallbackChain for
graceful degradation when the API is fully unavailable.
"""

from typing import Any

import requests

from config.settings import settings
from core.contracts import ToolName, ToolResult
from resilience.fallback import FallbackChain
from resilience.retry import retry_with_backoff
from tools.base import AbstractTool
from utils.logger import get_logger

logger = get_logger(__name__)

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherAPIError(Exception):
    """Raised when the OpenWeather API call fails. Narrow exception type,
    same reasoning as LLMError — lets retry logic target it specifically."""
    pass


class WeatherTool(AbstractTool):
    name = ToolName.WEATHER

    def execute(self, params: dict[str, Any], request_id: str) -> ToolResult:
        city = params.get("city", "")
        if not city:
            return ToolResult(
                request_id=request_id,
                tool_name=self.name,
                success=False,
                error_message="No city provided",
            )

        chain = FallbackChain([
            lambda: self._call_primary_api(city, request_id),
            lambda: self._graceful_degradation(city, request_id),
        ])
        return chain.run(request_id=request_id, tool_name=self.name)

    @retry_with_backoff(max_attempts=3, base_delay_seconds=1.0, retryable_exceptions=(WeatherAPIError,))
    def _call_primary_api(self, city: str, request_id: str) -> ToolResult:
        """Strategy 1: real OpenWeather call. Retries on transient failure
        (network issue, timeout) before FallbackChain considers it a failed strategy."""
        try:
            response = requests.get(
                OPENWEATHER_URL,
                params={
                    "q": city,
                    "appid": settings.openweather_api_key,
                    "units": "metric",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"[{request_id}] OpenWeather API call failed: {e}")
            raise WeatherAPIError(f"OpenWeather request failed: {e}") from e

        logger.info(f"[{request_id}] Weather fetched for {city}")
        return ToolResult(
            request_id=request_id,
            tool_name=self.name,
            success=True,
            data={
                "city": city,
                "temperature_celsius": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity_percent": data["main"]["humidity"],
            },
        )

    def _graceful_degradation(self, city: str, request_id: str) -> ToolResult:
        """Final strategy: primary API + retries exhausted. Return an honest,
        clear message instead of crashing or returning fake data."""
        logger.warning(f"[{request_id}] Weather unavailable for {city}, degrading gracefully")
        return ToolResult(
            request_id=request_id,
            tool_name=self.name,
            success=True,  # the TOOL succeeded at producing a coherent response,
                            # even though the underlying data wasn't available
            data={
                "city": city,
                "message": f"Weather data for {city} is temporarily unavailable. Please try again shortly.",
            },
        )