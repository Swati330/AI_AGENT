"""
Stage 4: Result Validation.
Takes a raw ToolResult, checks it's well-formed/usable before it reaches
the response generation stage. Pure, fast, deterministic — no LLM call,
no re-execution of the tool.
"""

import math

from core.contracts import ToolName, ToolResult, ValidatedResult
from utils.logger import get_logger

logger = get_logger(__name__)


class Validator:
    def __init__(self):
        self._checkers = {
            ToolName.CALCULATOR: self._check_calculator,
            ToolName.WEATHER: self._check_weather,
        }

    def validate(self, result: ToolResult) -> ValidatedResult:
        if not result.success:
            return ValidatedResult(
                request_id=result.request_id,
                tool_name=result.tool_name,
                is_valid=False,
                data=None,
                validation_notes=f"Tool reported failure: {result.error_message}",
            )

        checker = self._checkers.get(result.tool_name, self._default_check)
        is_valid, notes = checker(result)

        logger.info(f"[{result.request_id}] Validation for {result.tool_name.value}: {'passed' if is_valid else 'FAILED'}")

        return ValidatedResult(
            request_id=result.request_id,
            tool_name=result.tool_name,
            is_valid=is_valid,
            data=result.data if is_valid else None,
            validation_notes=notes,
        )

    def _check_calculator(self, result: ToolResult) -> tuple[bool, str]:
        value = result.data.get("result") if result.data else None
        if value is None:
            return False, "No result field in calculator output"
        if isinstance(value, (int, float)) and (math.isnan(value) or math.isinf(value)):
            return False, f"Calculator produced non-finite result: {value}"
        return True, "Numeric result within valid range"

    def _check_weather(self, result: ToolResult) -> tuple[bool, str]:
        if not result.data or "city" not in result.data:
            return False, "Missing city in weather output"
        if "message" in result.data:
            return True, "Graceful degradation message, valid to pass through"
        temp = result.data.get("temperature_celsius")
        if temp is None or not (-90 <= temp <= 60):
            return False, f"Temperature out of plausible range: {temp}"
        return True, "Weather data within plausible range"

    def _default_check(self, result: ToolResult) -> tuple[bool, str]:
        if not result.data:
            return False, "No data returned"
        return True, "Passed default validation (no tool-specific rules yet)"