"""
Configuration management for ReturnPilot Backend.
Loads environment variables and provides typed configuration access.
Validates all required environment variables on startup.
"""

import os
import sys
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = os.getenv("DATABASE_URL", "")

    # Claude API
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Supabase Storage
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")

    # Notification Service (optional)
    notification_service_url: Optional[str] = os.getenv("NOTIFICATION_SERVICE_URL")

    # CORS (comma-separated list of allowed origins)
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")

    # Application
    environment: str = os.getenv("ENVIRONMENT", "development")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_required(self):
        """
        Validate that all required environment variables are set.
        Called on application startup to fail fast if misconfigured.
        Requirements: 1.1, 1.5, 15.4, 15.6
        """
        required = {
            "DATABASE_URL": self.database_url,
            "ANTHROPIC_API_KEY": self.anthropic_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_KEY": self.supabase_key,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
            print("Please set them in your .env file.")
            sys.exit(1)


# Global settings instance
settings = Settings()

# Validate on import (startup)
settings.validate_required()
