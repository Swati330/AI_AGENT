"""
Fallback chain logic: primary provider -> backup provider -> cache -> graceful degradation.
Tool-agnostic — any tool can wrap its calls with this.

Implements the Chain of Responsibility pattern: each strategy is tried in
order, and the chain stops at the first one that succeeds. No strategy
knows about the others — the chain itself owns the sequencing.
"""

from typing import Callable

from core.contracts import ToolName, ToolResult
from utils.logger import get_logger

logger = get_logger(__name__)

# A strategy is any callable that attempts to produce a ToolResult.
# It should never raise — like AbstractTool.execute(), it returns
# ToolResult(success=False, ...) on failure so the chain can inspect it.
FallbackStrategy = Callable[[], ToolResult]


class FallbackChain:
    """Tries a sequence of strategies in order, stopping at the first success.

    Example usage (once WeatherTool exists):
        chain = FallbackChain([
            lambda: call_primary_weather_api(city),
            lambda: call_backup_weather_api(city),
            lambda: read_cached_weather(city),
        ])
        result = chain.run(request_id="abc123", tool_name=ToolName.WEATHER)
    """

    def __init__(self, strategies: list[FallbackStrategy]):
        if not strategies:
            raise ValueError("FallbackChain requires at least one strategy")
        self._strategies = strategies

    def run(self, request_id: str, tool_name: ToolName) -> ToolResult:
        last_result: ToolResult | None = None

        for i, strategy in enumerate(self._strategies, start=1):
            is_last_strategy = i == len(self._strategies)
            try:
                result = strategy()
            except Exception as e:
                # A strategy raising is itself a failure — treat it as one,
                # don't let it crash the whole chain.
                logger.warning(f"[{request_id}] Fallback strategy {i} raised: {e}")
                result = ToolResult(
                    request_id=request_id,
                    tool_name=tool_name,
                    success=False,
                    error_message=str(e),
                )

            if result.success:
                if i > 1:
                    result.used_fallback = True
                    logger.info(f"[{request_id}] Succeeded on fallback strategy {i}")
                return result

            last_result = result
            if not is_last_strategy:
                logger.warning(
                    f"[{request_id}] Strategy {i} failed, trying next fallback..."
                )

        # Every strategy failed — return the last failure, but make it
        # explicitly clear this is the FINAL, graceful-degradation outcome.
        logger.error(f"[{request_id}] All {len(self._strategies)} fallback strategies exhausted")
        return last_result