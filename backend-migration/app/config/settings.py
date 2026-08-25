"""
Configuration settings
"""
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        case_sensitive=False,
        extra="ignore",
    )
      
    # Scehma settings
    comet_schemas_path: str
    
    # API settings
    api_title: str = "Metadata Extractor API"
    api_version: str = "1.0.0"
    api_description: str = "Extract metadata from code repositories (GitHub)"
    
    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    # LLM settings (optional)
    llm_api_key: Optional[str] = None
    llm_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("README_LLM_ENABLED", "LLM_EXTRACTION_ENABLED", "llm_enabled"),
    )
    llm_provider: str = Field(
        default="groq",
        validation_alias=AliasChoices("README_LLM_PROVIDER", "LLM_EXTRACTION_PROVIDER", "llm_provider"),
    )  # groq, openai, etc.
    llm_model: str = Field(
        default="llama-3.1-70b-versatile",
        validation_alias=AliasChoices("README_LLM_MODEL", "LLM_EXTRACTION_MODEL", "llm_model"),
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("README_LLM_BASE_URL", "LLM_EXTRACTION_BASE_URL", "llm_base_url"),
    )
    
    # Logging
    log_level: str = "INFO"


settings = Settings()

