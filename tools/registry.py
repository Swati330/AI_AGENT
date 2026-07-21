"""
ToolRegistry — maps tool name -> tool instance.
Adding a new tool = write one class + one registration line here. Nothing else changes.
"""

from core.contracts import ToolName
from llm.client import GeminiClient
from tools.base import AbstractTool
from tools.calculator import CalculatorTool
from tools.weather import WeatherTool
from tools.wikipedia import WikipediaTool
from utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Central lookup for all available tools.

    Why a class instead of a bare dict: gives us one place to add
    lookup-time behavior later (logging, metrics, clear errors) without
    every caller needing to know it's "just a dict" under the hood.
    """

    def __init__(self):
        self._tools: dict[ToolName, AbstractTool] = {}

    def register(self, tool: AbstractTool) -> None:
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name.value}")

    def get(self, name: ToolName) -> AbstractTool:
        if name not in self._tools:
            raise ValueError(f"No tool registered for: {name}. Available: {list(self._tools.keys())}")
        return self._tools[name]

    def available_tools(self) -> list[ToolName]:
        return list(self._tools.keys())


def build_default_registry(llm_client: GeminiClient) -> ToolRegistry:
    """Factory function: builds and returns the registry with all current
    tools registered. WikipediaTool needs the llm_client for Hop 2
    (fact extraction), so it's passed in rather than created internally.
    This is the ONE place you touch when adding a new tool."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WeatherTool())
    registry.register(WikipediaTool(llm_client))
    return registry