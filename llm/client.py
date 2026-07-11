"""
Thin wrapper around the Gemini API. Knows nothing about tools or pipeline stages —
just takes a prompt, returns a response. Kept isolated so the LLM provider is swappable.
"""
