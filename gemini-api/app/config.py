"""
Configuration module for Gemini AI API
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Gemini AI API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 1
    
    # Google Gemini
    gemini_api_key: str
    gemini_model_id: str = "gemini-2.5-flash"
    gemini_fallback_model_id: str = "gemini-2.5-flash-lite"
    gemini_timeout: int = 30
    gemini_max_retries: int = 3
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 10
    rate_limit_period: int = 60  # seconds
    
    # Security
    api_key: str | None = None
    cors_origins: str = "*"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"


# Global settings instance
settings = Settings()
