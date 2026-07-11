"""
Single source of truth for all data shapes flowing through the pipeline.
Every pipeline stage takes a Pydantic model in and returns a Pydantic model out.
No stage should pass raw dicts to another stage.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enums — fixed, known vocabularies. Using Enum instead of raw strings
# turns "typo in intent name" from a silent runtime bug into an immediate
# validation error at the model boundary.
# ---------------------------------------------------------------------------

class IntentType(str, Enum):
    CALCULATION = "calculation"
    WEATHER_QUERY = "weather_query"
    KNOWLEDGE_QUERY = "knowledge_query"
    UNKNOWN = "unknown"


class ToolName(str, Enum):
    CALCULATOR = "calculator"
    WEATHER = "weather"
    WIKIPEDIA = "wikipedia"
    NONE = "none"  # used when Planning decides no tool is needed


# ---------------------------------------------------------------------------
# Stage 0 -> 1 boundary: what enters the pipeline
# ---------------------------------------------------------------------------

class AgentRequest(BaseModel):
    """The raw entry point. Even user input is typed, not a loose string
    floating through the system."""
    query: str = Field(..., min_length=1, description="Raw user query text")
    request_id: str = Field(..., description="Unique ID for tracing this request through logs")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Stage 1 -> 2 boundary: output of Intent Understanding
# ---------------------------------------------------------------------------

class Intent(BaseModel):
    """What does the user want? This stage does NOT decide how to fulfill it."""
    request_id: str
    intent_type: IntentType
    raw_query: str
    extracted_entities: dict[str, Any] = Field(
        default_factory=dict,
        description="e.g. {'city': 'Bhubaneswar'} for weather, {'expression': '2+2'} for calc",
    )
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


# ---------------------------------------------------------------------------
# Stage 2 -> 3 boundary: output of Planning (+ Tool Selection, merged for now)
# ---------------------------------------------------------------------------

class Plan(BaseModel):
    """What needs to happen to fulfill the intent, and which tool will do it.

    NOTE: Planning and Tool Selection are architecturally two separate
    responsibilities but are IMPLEMENTED as one function today, since we
    only route single-tool queries this week. `selected_tool` is already
    a first-class field so that splitting Planning and Selection into two
    real stages later requires zero changes to this contract — only
    planner.py and selector.py change internally.
    """
    request_id: str
    intent: Intent
    selected_tool: ToolName
    tool_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the tool's execute() method",
    )
    reasoning: str = Field(default="", description="Why this tool was chosen — useful for debugging/demo")


# ---------------------------------------------------------------------------
# Stage 3 -> 4 boundary: raw output of Tool Execution
# ---------------------------------------------------------------------------

class ToolResult(BaseModel):
    """Raw result from a tool call. success=False does NOT mean the pipeline
    crashed — it means the tool failed and the fallback/validation stages
    need to handle that explicitly, not via exceptions."""
    request_id: str
    tool_name: ToolName
    success: bool
    data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    used_fallback: bool = Field(
        default=False,
        description="True if a backup provider/cache was used instead of the primary source",
    )


# ---------------------------------------------------------------------------
# Stage 4 -> 5 boundary: output of Result Validation
# ---------------------------------------------------------------------------

class ValidatedResult(BaseModel):
    """A DISTINCT type from ToolResult, not just a bool flip.

    Why a separate model instead of reusing ToolResult with is_valid=True:
    if core/responder.py's function signature only accepts ValidatedResult,
    it becomes structurally impossible to accidentally pass an unvalidated
    ToolResult into response generation. The type system documents and
    enforces the pipeline order.
    """
    request_id: str
    tool_name: ToolName
    is_valid: bool
    data: Optional[dict[str, Any]] = None
    validation_notes: str = Field(default="", description="Why it passed/failed validation")


# ---------------------------------------------------------------------------
# Final boundary: what leaves the pipeline
# ---------------------------------------------------------------------------

class AgentResponse(BaseModel):
    """The final answer returned to the user via the API."""
    request_id: str
    answer: str
    success: bool
    intent_type: IntentType
    tool_used: ToolName
    used_fallback: bool = False
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Pipeline event — for the "Thinking... Planning... Executing..." UI later.
# Cheap to add now, painful to retrofit after stages are built.
# ---------------------------------------------------------------------------

class PipelineEvent(BaseModel):
    request_id: str
    stage_name: str
    status: str = Field(description="'started' | 'completed' | 'failed'")
    detail: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.utcnow)