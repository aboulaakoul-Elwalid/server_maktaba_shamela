# app/config/settings.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings using Pydantic's BaseSettings."""
    # API configuration
    API_TITLE: str = "Arabia RAG API"
    API_DESCRIPTION: str = "Retrieval-Augmented Generation API for Shamela Library"
    API_VERSION: str = "0.1.0"
    API_KEY_REQUIRED: bool = True
    PORT: int = 8000
    
    # CORS configuration
    CORS_ORIGINS: List[str] = ["*"]
    
    # External service API keys
    MISTRAL_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "shamela"
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"
    
    # Optional LLM keys
    OPENAI_API_KEY: Optional[str] = None
    
    # Document processing
    MAX_CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # Arabic-specific settings
    NORMALIZE_ARABIC: bool = True  # Remove diacritics/normalize for matching
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Appwrite settings
    APPWRITE_ENDPOINT: str
    APPWRITE_PROJECT_ID: str
    APPWRITE_API_KEY: str
    
    class Config:
        """Inner configuration class for Pydantic settings."""
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    """Create and cache a Settings instance."""
    return Settings()

# Create a singleton instance for importing elsewhere
settings = get_settings()