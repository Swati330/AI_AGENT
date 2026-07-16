"""
Stage 2: Planning (+ Tool Selection, merged for now — see contracts.py note).
Takes an Intent, decides which tool to use and what parameters to pass it.
Deterministic mapping, no LLM call needed — the Intent already carries
what's needed; this stage just routes it.
"""

from core.contracts import Intent, IntentType, Plan, ToolName
from utils.logger import get_logger

logger = get_logger(__name__)

# IntentType -> ToolName mapping. Adding a new intent/tool pair = one new line here.
_INTENT_TO_TOOL = {
    IntentType.CALCULATION: ToolName.CALCULATOR,
    IntentType.WEATHER_QUERY: ToolName.WEATHER,
    IntentType.KNOWLEDGE_QUERY: ToolName.WIKIPEDIA,
}


class Planner:
    def plan(self, intent: Intent) -> Plan:
        if intent.intent_type == IntentType.UNKNOWN:
            return Plan(
                request_id=intent.request_id,
                intent=intent,
                selected_tool=ToolName.NONE,
                tool_params={},
                reasoning="Intent could not be classified; no tool selected.",
            )

        selected_tool = _INTENT_TO_TOOL.get(intent.intent_type, ToolName.NONE)
        tool_params = self._build_params(intent, selected_tool)

        logger.info(f"[{intent.request_id}] Planned tool: {selected_tool.value}")
        return Plan(
            request_id=intent.request_id,
            intent=intent,
            selected_tool=selected_tool,
            tool_params=tool_params,
            reasoning=f"Intent '{intent.intent_type.value}' maps to tool '{selected_tool.value}'.",
        )

    def _build_params(self, intent: Intent, tool: ToolName) -> dict:
        """Translate extracted_entities into the specific param shape each tool expects."""
        if tool == ToolName.CALCULATOR:
            return {"expression": intent.extracted_entities.get("expression", "")}
        if tool == ToolName.WEATHER:
            return {"city": intent.extracted_entities.get("city", "")}
        if tool == ToolName.WIKIPEDIA:
            return {"topic": intent.extracted_entities.get("topic", "")}
        return {}