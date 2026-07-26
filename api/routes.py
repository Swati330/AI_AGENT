"""
HTTP routes. Thin by design: deserialize request -> call orchestrator -> serialize response.
No business logic should live here.
"""

from functools import lru_cache

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.orchestrator import Orchestrator, build_default_orchestrator

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


@lru_cache
def get_orchestrator() -> Orchestrator:
    """Built once, reused across all requests — avoids re-creating the
    GeminiClient/ToolRegistry/etc. on every single call. @lru_cache with
    no arguments acts as a simple singleton here."""
    return build_default_orchestrator()


@router.post("/query")
def query_agent(request: QueryRequest, orchestrator: Orchestrator = Depends(get_orchestrator)):
    response = orchestrator.run(request.query)
    return response