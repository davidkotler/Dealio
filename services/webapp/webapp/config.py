"""Application configuration via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="forbid")

    database_url: Annotated[str, Field(description="PostgreSQL async connection URL (asyncpg)")]
    jwt_secret: Annotated[str, Field(description="Secret key for signing JWT tokens")]
    aws_region: Annotated[str, Field(default="us-east-1", description="AWS region for service calls")]
    scraper_lambda_name: Annotated[str, Field(description="Name of the scraper Lambda function")]
    ses_from_address: Annotated[str, Field(description="SES verified sender address for emails")]
    google_client_id: Annotated[str, Field(description="Google OAuth2 client ID")]
    google_client_secret: Annotated[str, Field(description="Google OAuth2 client secret")]
    google_redirect_uri: Annotated[str, Field(description="Google OAuth2 redirect URI")]
    app_base_url: Annotated[str, Field(description="Public base URL for building password reset links")]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
