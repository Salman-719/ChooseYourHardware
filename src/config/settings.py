"""Application settings using Pydantic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    # API Configuration
    app_version: str = "1.0.0"
    environment: str = Field("development", alias="ENV")
    api_title: str = "ChooseYourHardware API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4.1-2025-04-14", alias="OPENAI_LLM_MODEL")
    # Hardware Defaults
    default_utilization_fp32: float = 0.5
    default_utilization_fp16: float = 0.5
    default_utilization_bf16: float = 0.5
    default_utilization_int8: float = 0.5

    # Logging
    log_level: str = "INFO"
    log_format: str = "text"  # "json" or "text"

    # CORS
    cors_origins: list[str] = ["*"]

    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance.

    Returns:
        Settings singleton instance
    """
    return settings
