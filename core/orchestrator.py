"""
Wires all pipeline stages together in sequence.
Emits pipeline stage events (for logging now, for UI streaming later).
This is the ONLY place that knows the full pipeline order — every other
stage only knows its own input/output contract, not what comes before/after.
"""

import uuid

from core.contracts import (
    AgentRequest,
    AgentResponse,
    IntentType,
    PipelineEvent,
    ToolName,
)
from core.intent import IntentUnderstander, IntentUnderstandingError
from core.planner import Planner
from core.responder import Responder
from core.validator import Validator
from llm.client import GeminiClient
from tools.registry import ToolRegistry, build_default_registry
from utils.logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    def __init__(
        self,
        intent_understander: IntentUnderstander,
        planner: Planner,
        tool_registry: ToolRegistry,
        validator: Validator,
        responder: Responder,
    ):
        self._intent_understander = intent_understander
        self._planner = planner
        self._tool_registry = tool_registry
        self._validator = validator
        self._responder = responder

    def run(self, query: str) -> AgentResponse:
        request_id = str(uuid.uuid4())[:8]
        request = AgentRequest(query=query, request_id=request_id)

        self._emit_event(request_id, "pipeline", "started", f"Query: {query}")

        # Stage 1: Intent Understanding
        self._emit_event(request_id, "intent_understanding", "started")
        try:
            intent = self._intent_understander.understand(request)
        except IntentUnderstandingError as e:
            self._emit_event(request_id, "intent_understanding", "failed", str(e))
            return AgentResponse(
                request_id=request_id,
                answer="The agent is temporarily unavailable. Please try again in a moment.",
                success=False,
                intent_type=IntentType.UNKNOWN,
                tool_used=ToolName.NONE,
            )
        self._emit_event(request_id, "intent_understanding", "completed", intent.intent_type.value)

        # Early exit: unknown intent, no tool to run
        if intent.intent_type == IntentType.UNKNOWN:
            self._emit_event(request_id, "pipeline", "completed", "unknown intent, no tool run")
            return self._responder.respond_unknown_intent(request_id)

        # Stage 2: Planning + Tool Selection (merged)
        self._emit_event(request_id, "planning", "started")
        plan = self._planner.plan(intent)
        self._emit_event(request_id, "planning", "completed", plan.selected_tool.value)

        # Stage 3: Tool Execution
        self._emit_event(request_id, "tool_execution", "started", plan.selected_tool.value)
        tool = self._tool_registry.get(plan.selected_tool)
        tool_result = tool.execute(plan.tool_params, request_id)
        self._emit_event(request_id, "tool_execution", "completed", f"success={tool_result.success}")

        # Stage 4: Validation
        self._emit_event(request_id, "validation", "started")
        validated = self._validator.validate(tool_result)
        self._emit_event(request_id, "validation", "completed", f"valid={validated.is_valid}")

        # Stage 5: Response Generation
        self._emit_event(request_id, "response_generation", "started")
        response = self._responder.respond(validated, intent.intent_type)
        self._emit_event(request_id, "response_generation", "completed")

        self._emit_event(request_id, "pipeline", "completed")
        return response

    def _emit_event(self, request_id: str, stage_name: str, status: str, detail: str = "") -> None:
        """Emit a pipeline stage event. Currently just logs it — this is the
        hook point for streaming these to a UI later (the 'Thinking...
        Planning... Executing...' visualization from the original spec)
        without changing anything else in the pipeline."""
        event = PipelineEvent(request_id=request_id, stage_name=stage_name, status=status, detail=detail)
        logger.info(f"[{request_id}] {stage_name} :: {status} :: {detail}")


def build_default_orchestrator() -> Orchestrator:
    """Factory function: wires up all real dependencies. This is the ONE
    place the whole app gets assembled — api/routes.py will call this."""
    llm_client = GeminiClient()
    return Orchestrator(
        intent_understander=IntentUnderstander(llm_client),
        planner=Planner(),
        tool_registry=build_default_registry(),
        validator=Validator(),
        responder=Responder(llm_client),
    )