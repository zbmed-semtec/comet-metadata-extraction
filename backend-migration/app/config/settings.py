"""
Configuration settings
"""
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
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
    
    # LLM settings
    llm_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("README_LLM_ENABLED", "LLM_EXTRACTION_ENABLED", "llm_enabled"),
    )
    llm_provider: str = Field(
        default="ollama",
        validation_alias=AliasChoices("README_LLM_PROVIDER", "LLM_EXTRACTION_PROVIDER", "llm_provider"),
    )
    llm_model: str = Field(
        default="qwen2.5:7b",
        validation_alias=AliasChoices("README_LLM_MODEL", "LLM_EXTRACTION_MODEL", "llm_model"),
    )
    llm_base_url: str = Field(
        default="http://localhost:11435",
        validation_alias=AliasChoices(
            "README_LLM_BASE_URL",
            "LLM_EXTRACTION_BASE_URL",
            "OLLAMA_HOST",
            "llm_base_url",
        ),
    )

    @field_validator("llm_base_url", mode="before")
    @classmethod
    def normalize_llm_base_url(cls, value: object) -> str:
        """Accept a conventional Ollama host value as an HTTP base URL."""
        if value is None or not str(value).strip():
            return "http://localhost:11434"

        base_url = str(value).strip().rstrip("/")
        if "://" not in base_url:
            base_url = f"http://{base_url}"
        return base_url
    
    # Logging
    log_level: str = "INFO"


settings = Settings()
