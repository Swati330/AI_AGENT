# AI Agent — Built From Scratch

A modular AI agent built without agent frameworks (no LangChain, LangGraph, CrewAI, or AutoGen) — every stage of the pipeline is hand-built, using Python, FastAPI, and the Gemini API.

## Why no framework?

The goal wasn't just to ship a working agent — it was to actually understand how one works internally: how it classifies intent, selects tools, handles failure, and recovers, without relying on a library to make those decisions invisibly.

## Architecture

An 8-stage pipeline, with typed data contracts (Pydantic) between every stage so malformed data fails immediately instead of corrupting something downstream:

User Query
↓
Intent Understanding — classifies the request via Gemini
↓
Planning + Tool Selection — deterministic routing, no LLM call needed
↓
Tool Execution — calculator, weather, or Wikipedia
↓
Result Validation — checks the output is actually sane
↓
Response Generation — natural language answer via Gemini
↓
Final Response

Every stage is independent and replaceable — no stage knows what happens before or after it, only its own input/output contract.

## Tools

| Tool | What it does | Notes |
|---|---|---|
| **Calculator** | Evaluates math expressions | Uses Python's `ast` module for safe, whitelisted evaluation — deliberately avoids `eval()`, which is a code-injection risk |
| **Weather** | Live weather via OpenWeather | Wrapped in retry-with-backoff and a fallback chain for graceful degradation on failure |
| **Wikipedia** | Multi-hop lookup | Resolves the entity first, then extracts a specific fact from the page content — a simplified retrieve-then-extract pattern, not just a summary lookup |

## Resilience

- **Retry with exponential backoff** — wraps calls to Gemini and external APIs, retries transient failures with increasing delay
- **Fallback chain (Chain of Responsibility)** — tries a sequence of strategies (primary source → graceful degradation) and stops at the first success
- Both have been tested against real failures during development, including an actual Gemini API outage — not just simulated ones

## Tech stack

- **Backend:** FastAPI + Uvicorn
- **Validation:** Pydantic v2
- **LLM:** Google Gemini (`google-genai` SDK)
- **Tools:** `ast` (stdlib), `requests`, `wikipedia-api`
- **Config:** `pydantic-settings` + `.env`
- **Frontend:** standalone HTML/CSS/JS, calls the API directly — no build step

## Project structure
config/ — typed settings, loaded from .env
core/ — pipeline stages (intent, planner, validator, responder, orchestrator)
tools/ — pluggable tool implementations + registry
llm/ — Gemini client wrapper + prompt templates
resilience/ — retry and fallback logic
api/ — FastAPI app and routes
utils/ — logging setup

## Running it

```bash
# activate your virtual environment first
pip install -r requirements.txt

# add your API keys to .env — see .env.example
uvicorn api.main:app --reload
```

Server runs at `http://127.0.0.1:8000`.

- Interactive API docs: `http://127.0.0.1:8000/docs`
- Chat frontend: open `agent_chat.html` directly in a browser (requires the server to be running)

## Example queries

- `"what is 45 divided by 9"` → calculator
- `"weather in Bhubaneswar"` → live weather lookup
- `"who is Isaac Newton"` → Wikipedia (single-hop)
- `"what is the capital of Sri Lanka"` → Wikipedia (multi-hop — resolves the entity, then extracts the specific fact)
- gibberish input → gracefully falls back to "could you rephrase that," without wasting a tool call

## Known limitations (deliberately scoped out for now)

- **Single-hop tool selection per query** — one query resolves to one tool call; chaining multiple tool calls together isn't implemented yet
- **No conversation memory** — each query is processed independently; follow-up questions that rely on prior context aren't resolved automatically
- **Out-of-scope queries** (e.g. small talk) correctly return a graceful "not sure what you're asking" rather than attempting to handle them — the agent is intentionally narrow in scope, not a general chatbot

## Roadmap

- Conversation memory / session context
- Multi-hop tool chaining across different tools, not just within Wikipedia
- Docker + deployment
- Streaming pipeline events to the frontend in real time (currently the frontend animates a reasonable approximation, since the API is request/response, not streaming)

