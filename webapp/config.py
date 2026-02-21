from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name: str = "Who Am I? – LLM Persona Game"
    app_version: str = "1.0.0"
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./whoami.db")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = "claude-sonnet-4-6"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
