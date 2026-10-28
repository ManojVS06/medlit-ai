"""
Application configuration loaded from environment variables.

WHY THIS EXISTS:
- Configuration (API keys, database URLs, ports) should NEVER be hardcoded.
- pydantic-settings reads from .env files and environment variables automatically.
- If a required variable is missing, Pydantic raises a clear error at startup
  instead of crashing mysteriously later.

HOW IT WORKS:
- BaseSettings looks for a .env file and loads variables from it.
- Each field has a type and optionally a default value.
- Accessing `settings.LLM_PROVIDER` anywhere in the app gives you the configured value.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the MedLit AI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Don't fail on unknown env vars
    )

    # --- App ---
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 5173

    # --- LLM ---
    LLM_PROVIDER: str = "mock"  # "mock", "gemini", or "ollama"
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- PubMed / NCBI ---
    NCBI_API_KEY: str = ""
    NCBI_EMAIL: str = ""
    NCBI_TOOL: str = "medlit-ai"

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./medlit.db"


# Singleton instance — import this wherever you need config
settings = Settings()
