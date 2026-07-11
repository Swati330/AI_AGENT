"""
Typed application settings, loaded from environment variables via pydantic-settings.
Every other module reads config from here — never call os.environ directly elsewhere.
"""
