"""
Typed application settings, loaded from environment variables via pydantic-settings.
Every other module reads config from here — never call os.environ directly elsewhere.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: str
    openweather_api_key: str = ""  # optional for now, needed when weather tool is built

    gemini_model_name: str = "gemini-3.5-flash"
    llm_timeout_seconds: int = 15


# Singleton instance — import this everywhere instead of creating Settings() repeatedly
settings = Settings()