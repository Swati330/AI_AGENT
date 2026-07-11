"""
AbstractTool — the common interface every tool must implement.
Enforced via ABC so a tool literally cannot be instantiated without implementing execute().
"""

from abc import ABC, abstractmethod
from typing import Any

from core.contracts import ToolName, ToolResult


class AbstractTool(ABC):
    """Base class every tool (Calculator, Weather, Wikipedia, ...) must extend.

    Design contract:
    - Each tool declares its own `name` (a ToolName enum member) so the
      registry can key on it consistently with the rest of the pipeline.
    - `execute()` must NEVER let an exception escape to the caller. Any
      external failure (API down, timeout, bad input) is caught internally
      and translated into ToolResult(success=False, error_message=...).
      This keeps failure handling declarative and centralized in
      resilience/fallback.py, instead of scattered try/except blocks
      throughout the pipeline.
    """

    name: ToolName  # every subclass must set this as a class attribute

    @abstractmethod
    def execute(self, params: dict[str, Any], request_id: str) -> ToolResult:
        """Run the tool with the given parameters.

        Args:
            params: tool-specific arguments (e.g. {'expression': '2+2'})
            request_id: for tracing this call through logs

        Returns:
            ToolResult — success=True with data, or success=False with
            error_message. Never raises.
        """
        raise NotImplementedError