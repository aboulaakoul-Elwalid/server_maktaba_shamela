# app/config/settings.py
from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import os
from functools import lru_cache
from pydantic import field_validator, model_validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings using Pydantic's BaseSettings."""
    # API configuration
    API_TITLE: str = "Arabia RAG API"
    API_DESCRIPTION: str = "Retrieval-Augmented Generation API for Shamela Library"
    API_VERSION: str = "0.1.0"
    API_KEY_REQUIRED: bool = True
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # CORS configuration - changed from List[str] to str for compatibility
    CORS_ORIGINS: str = "*"
    
    # External service API keys
    MISTRAL_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "shamela"
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"
    
    # Optional LLM keys
    OPENAI_API_KEY: Optional[str] = None
    API_KEY_GOOGLE: Optional[str] = os.getenv("API_KEY_GOOGLE", None)
    
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
    APPWRITE_DATABASE_ID: str = "arabia_db"
    
    # Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-should-be-at-least-32-characters-long")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # These were causing errors - add them as optionals
    ALLOWED_HOSTS: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    
    class Config:
        """Inner configuration class for Pydantic settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields to prevent errors with environment variables
        extra = "ignore"  # Changed to ignore extra fields

@lru_cache()
def get_settings() -> Settings:
    """Create and cache a Settings instance."""
    return Settings()

# Create a singleton instance for importing elsewhere
settings = get_settings()