"""
FastAPI app instance and startup config. Kept minimal.
"""

from fastapi import FastAPI

from api.routes import router

app = FastAPI(
    title="AI Agent",
    description="A modular AI agent built from scratch — no agent frameworks.",
    version="0.1.0",
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only — fine for local demo, not for real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health_check():
    """Basic liveness check — confirms the service is up, not that every
    dependency (Gemini, OpenWeather) is reachable."""
    return {"status": "ok"}
