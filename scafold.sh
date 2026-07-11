#!/bin/bash
# scaffold.sh — creates the full ai-agent project structure
# Usage: bash scaffold.sh

set -e

ROOT="ai-agent"

echo "Creating project structure under ./$ROOT ..."

mkdir -p "$ROOT"/{config,core,tools,llm,resilience,api,utils,tests}

# --- root files ---
touch "$ROOT/.gitignore"
cat > "$ROOT/.gitignore" << 'EOF'
.env
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
*.egg-info/
EOF

cat > "$ROOT/.env.example" << 'EOF'
GEMINI_API_KEY=your_gemini_api_key_here
OPENWEATHER_API_KEY=your_openweather_api_key_here
EOF

cp "$ROOT/.env.example" "$ROOT/.env"

cat > "$ROOT/requirements.txt" << 'EOF'
fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-dotenv
google-generativeai
requests
wikipedia
pytest
EOF

cat > "$ROOT/README.md" << 'EOF'
# AI Agent — Built From Scratch

A modular AI agent built without agent frameworks (no LangChain/LangGraph/CrewAI).
Architecture and design decisions documented here as the project evolves.
EOF

# --- config ---
touch "$ROOT/config/__init__.py"
cat > "$ROOT/config/settings.py" << 'EOF'
"""
Typed application settings, loaded from environment variables via pydantic-settings.
Every other module reads config from here — never call os.environ directly elsewhere.
"""
EOF

# --- core ---
touch "$ROOT/core/__init__.py"
cat > "$ROOT/core/contracts.py" << 'EOF'
"""
Single source of truth for all data shapes flowing through the pipeline.
Every pipeline stage takes a Pydantic model in and returns a Pydantic model out.
No stage should pass raw dicts to another stage.
"""
EOF

cat > "$ROOT/core/intent.py" << 'EOF'
"""
Stage 1: Intent Understanding.
Takes the raw user query, returns a structured Intent (what does the user want?).
Does NOT decide which tool to use — that's Planning's job.
"""
EOF

cat > "$ROOT/core/planner.py" << 'EOF'
"""
Stage 2: Planning.
Takes an Intent, decides WHAT needs to happen (which tool(s), in what order).
Does NOT execute anything — that's Tool Execution's job.
"""
EOF

cat > "$ROOT/core/selector.py" << 'EOF'
"""
Stage 3: Tool Selection.
Takes a Plan, maps it to actual Tool instances via the ToolRegistry.
"""
EOF

cat > "$ROOT/core/validator.py" << 'EOF'
"""
Stage 4: Result Validation.
Takes a raw ToolResult, checks it's well-formed/usable before it reaches the response stage.
"""
EOF

cat > "$ROOT/core/responder.py" << 'EOF'
"""
Stage 5: Response Generation.
Takes a validated result, produces the final natural-language answer via Gemini.
Separate LLM call from Intent Understanding — different responsibility, different prompt.
"""
EOF

cat > "$ROOT/core/orchestrator.py" << 'EOF'
"""
Wires all pipeline stages together in sequence.
Emits pipeline stage events (for logging now, for UI streaming later).
This is the ONLY place that knows the full pipeline order.
"""
EOF

# --- tools ---
touch "$ROOT/tools/__init__.py"
cat > "$ROOT/tools/base.py" << 'EOF'
"""
AbstractTool — the common interface every tool must implement.
Enforced via ABC so a tool literally cannot be instantiated without implementing execute().
"""
EOF

cat > "$ROOT/tools/registry.py" << 'EOF'
"""
ToolRegistry — maps tool name -> tool instance.
Adding a new tool = write one class + one registration line here. Nothing else changes.
"""
EOF

cat > "$ROOT/tools/calculator.py" << 'EOF'
"""
CalculatorTool — implements AbstractTool. Pure Python, no external API.
"""
EOF

cat > "$ROOT/tools/weather.py" << 'EOF'
"""
WeatherTool — implements AbstractTool. Wraps OpenWeather API, uses resilience/fallback.py.
"""
EOF

cat > "$ROOT/tools/wikipedia.py" << 'EOF'
"""
WikipediaTool — implements AbstractTool. Wraps the Wikipedia API/library.
"""
EOF

# --- llm ---
touch "$ROOT/llm/__init__.py"
cat > "$ROOT/llm/client.py" << 'EOF'
"""
Thin wrapper around the Gemini API. Knows nothing about tools or pipeline stages —
just takes a prompt, returns a response. Kept isolated so the LLM provider is swappable.
"""
EOF

cat > "$ROOT/llm/prompts.py" << 'EOF'
"""
Prompt templates as constants/functions. Keeping prompts out of logic files
makes them easy to iterate on and review independently.
"""
EOF

# --- resilience ---
touch "$ROOT/resilience/__init__.py"
cat > "$ROOT/resilience/retry.py" << 'EOF'
"""
Retry-with-backoff decorator. For transient failures against the SAME provider.
"""
EOF

cat > "$ROOT/resilience/fallback.py" << 'EOF'
"""
Fallback chain logic: primary provider -> backup provider -> cache -> graceful degradation.
Tool-agnostic — any tool can wrap its calls with this.
"""
EOF

# --- api ---
touch "$ROOT/api/__init__.py"
cat > "$ROOT/api/main.py" << 'EOF'
"""
FastAPI app instance and startup config. Kept minimal.
"""
EOF

cat > "$ROOT/api/routes.py" << 'EOF'
"""
HTTP routes. Thin by design: deserialize request -> call orchestrator -> serialize response.
No business logic should live here.
"""
EOF

# --- utils ---
touch "$ROOT/utils/__init__.py"
cat > "$ROOT/utils/logger.py" << 'EOF'
"""
Centralized logging setup. Every module gets its logger via logging.getLogger(__name__).
"""
EOF

# --- tests ---
touch "$ROOT/tests/__init__.py"
cat > "$ROOT/tests/test_tools.py" << 'EOF'
"""
Unit tests for tools — start here since tools are the easiest to test in isolation
(pure input -> output, no pipeline context needed).
"""
EOF

echo ""
echo "Done. Structure created:"
find "$ROOT" -print | sed -e "s;[^/]*/;  |;g;s;  |\([^|]\);  +--\1;"

echo ""
echo "Next steps:"
echo "  cd $ROOT"
echo "  python -m venv venv"
echo "  source venv/bin/activate   # or venv\\Scripts\\activate on Windows"
echo "  pip install -r requirements.txt"
echo "  Add your real API keys to .env"