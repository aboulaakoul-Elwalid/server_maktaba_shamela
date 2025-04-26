# app/config/settings.py
from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import os
from functools import lru_cache
from pydantic import field_validator, model_validator
from dotenv import load_dotenv

# Load environment variables from .env file *before* defining Settings
load_dotenv()

class Settings(BaseSettings):
    """Application settings using Pydantic's BaseSettings."""
    # API configuration
    API_TITLE: str = "Arabia RAG API"
    API_DESCRIPTION: str = "Retrieval-Augmented Generation API for Shamela Library"
    API_VERSION: str = "0.1.0"
    API_KEY_REQUIRED: bool = True  # Note: This seems like a custom flag, not directly used by FastAPI itself
    PORT: int = 8000
    DEBUG: bool = False

    # CORS configuration - Use List[str] or str, depending on FastAPI version/needs
    # If using '*', a string is fine. If multiple specific origins, use List[str]
    CORS_ORIGINS: Union[str, List[str]] = "*"  # Default to '*'

    # External service API keys (Required - will raise error if not in env/.env)
    MISTRAL_API_KEY: str
    PINECONE_API_KEY: str
    APPWRITE_ENDPOINT: str
    APPWRITE_PROJECT_ID: str
    APPWRITE_API_KEY: str
    APPWRITE_CONVERSATIONS_COLLECTION_ID: str
    APPWRITE_MESSAGES_COLLECTION_ID: str
    APPWRITE_MESSAGE_SOURCES_COLLECTION_ID: str

    # Optional LLM keys (Defaults to None if not in env/.env)
    OPENAI_API_KEY: Optional[str] = None
    API_KEY_GOOGLE: Optional[str] = None

        # Arabic-specific settings
    NORMALIZE_ARABIC: bool = True

     # LLM Configuration # Added section
    LLM_TIMEOUT: int = 45
    MISTRAL_MODEL: str = "mistral-saba-2502" # Changed from mistral-saba-2502 based on previous code
    MISTRAL_TEMPERATURE: float = 0.7
    MISTRAL_MAX_TOKENS: int = 1000
    MISTRAL_API_ENDPOINT: str = "https://api.mistral.ai/v1/chat/completions"
    GEMINI_MODEL: str = "gemini-2.0-flash" # Changed from gemini-2.0-flash based on previous code

    # Pinecone specific (Defaults can be set here)
    PINECONE_INDEX_NAME: str = "shamela"
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"  # Or load from env if needed
    RETRIEVAL_TOP_K: int = 5 # Added
    # Appwrite specific (Defaults can be set here)
    APPWRITE_DATABASE_ID: str = "arabia_db"  # Or load from env if needed


    # Rate Limiting Settings (Defaults here, BaseSettings loads from env)
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_REQUESTS: int = 20

    # Document processing
    MAX_CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

     # Streaming Configuration # Added section
    STREAM_CHUNK_SIZE: int = 50
    STREAM_CHUNK_DELAY: float = 0.02

    # Prompt Configuration # Added section
    # Using a simple placeholder, replace with your actual multi-line prompt
    PROMPT_TEMPLATE: str = """You are a helpful assistant specializing in Arabic and Islamic texts. Use the following context derived from reliable sources to answer the user's question accurately and concisely. If the context does not contain the answer, state that the information is not available in the provided sources. Do not make up information. Cite the relevant Document ID (e.g., [ID: 1234_5_6]) when using information from the context."""

    # Arabic-specific settings
    NORMALIZE_ARABIC: bool = True

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Authentication (Use defaults here, BaseSettings loads from env)
    SECRET_KEY: str = "your-secret-key-should-be-at-least-32-characters-long"  # CHANGE THIS IN PRODUCTION
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Default to 60 minutes

    # Rate Limiting Settings (Defaults here, BaseSettings loads from env)
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_REQUESTS: int = 20

    # Optional settings (if needed, but often not required for basic FastAPI)
    ALLOWED_HOSTS: Optional[str] = None  # Usually handled by CORS or deployment server
    DATABASE_URL: Optional[str] = None  # Only if using a relational DB via SQLAlchemy etc.

    # --- Validators ---
    # You only need validators for complex checks or transformations.
    # Pydantic automatically validates types and required fields.
    # This validator ensures Appwrite IDs are non-empty if provided.
    @field_validator(
        'APPWRITE_PROJECT_ID', 'APPWRITE_API_KEY', 'APPWRITE_DATABASE_ID',
        'APPWRITE_CONVERSATIONS_COLLECTION_ID', 'APPWRITE_MESSAGES_COLLECTION_ID',
        'APPWRITE_MESSAGE_SOURCES_COLLECTION_ID',
        # Add other required fields like MISTRAL_API_KEY, PINECONE_API_KEY etc. if you want explicit checks
        'MISTRAL_API_KEY', 'PINECONE_API_KEY', 'APPWRITE_ENDPOINT',
        mode='before'  # Check before type validation
    )
    def check_required_string_settings(cls, v, info):
        if not isinstance(v, str) or v.strip() == "":
            # Raise ValueError if the field is required and empty/missing
            # Pydantic handles required fields automatically, but this adds an explicit non-empty check
            raise ValueError(f"{info.field_name} must be a non-empty string set in environment variables or .env file")
        return v

    # --- Pydantic Config ---
    class Config:
        """Inner configuration class for Pydantic settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from env/dotenv

# --- Singleton Pattern ---
@lru_cache()
def get_settings() -> Settings:
    """Create and cache a Settings instance. Ensures env vars are loaded."""
    try:
        return Settings()
    except ValueError as e:
        # Catch validation errors during settings creation
        print(f"ERROR: Configuration validation failed: {e}")
        # Depending on severity, you might exit or raise a more specific exception
        raise SystemExit(f"Configuration error: {e}")

# Create a singleton instance for importing elsewhere
settings = get_settings()

# Optional: Print a confirmation or some settings on startup (if DEBUG)
# if settings.DEBUG:
#    print("--- Settings Loaded ---")
#    print(f"Debug Mode: {settings.DEBUG}")
#    print(f"Appwrite Endpoint: {settings.APPWRITE_ENDPOINT}")
#    print(f"Log Level: {settings.LOG_LEVEL}")
#    print("-----------------------")