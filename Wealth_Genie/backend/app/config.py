import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_SERVICE_ROLE_KEY: str
    PORT: int = 8000

    # --- Milestone 3: LLM provider configuration ---
    # Provider-independent: business logic never imports a vendor SDK directly.
    LLM_PROVIDER: str = "claude"
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "claude-sonnet-4-6"

    # Extraction tuning
    OCR_TEXT_THRESHOLD_CHARS: int = 50  # below this, a PDF is treated as scanned
    MAX_OCR_PAGES: int = 15

    # Enable reading from .env and .env.local file
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
