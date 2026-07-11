"""
Fallback chain logic: primary provider -> backup provider -> cache -> graceful degradation.
Tool-agnostic — any tool can wrap its calls with this.
"""
