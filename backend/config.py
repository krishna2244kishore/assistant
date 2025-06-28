"""
Configuration and environment settings for the Calendar Booking Assistant.
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field, HttpUrl, validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # Application settings
    APP_NAME: str = "Calendar Booking Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "false").lower() == "true"
    
    # CORS settings
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # Google Calendar settings
    GOOGLE_CALENDAR_ENABLED: bool = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    GOOGLE_TOKEN_PATH: str = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @validator("CORS_ORIGINS")
    def assemble_cors_origins(cls, v):
        """Convert CORS_ORIGINS from string to list."""
        if isinstance(v, str) and v != "*":
            return [origin.strip() for origin in v.split(",")]
        elif v == "*":
            return ["*"]
        return v

# Create settings instance
settings = Settings()

# Configure logging
import logging
from logging.config import dictConfig

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": settings.LOG_LEVEL},
        "uvicorn": {"handlers": ["default"], "level": settings.LOG_LEVEL, "propagate": False},
        "uvicorn.error": {"level": settings.LOG_LEVEL},
        "uvicorn.access": {"handlers": ["default"], "level": settings.LOG_LEVEL, "propagate": False},
    },
}

dictConfig(log_config)
logger = logging.getLogger(__name__)

# Log configuration on startup
if settings.DEBUG:
    import json
    logger.info("Application configuration:")
    logger.info(json.dumps(settings.dict(), indent=2, default=str))
