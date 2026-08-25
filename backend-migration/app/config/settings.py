"""
Configuration settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

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
    llm_model: str = "llama-3.1-70b-versatile"
    llm_provider: str = "groq"  # groq, openai, etc.
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

