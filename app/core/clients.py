# app/core/clients.py
"""
Client module for external service initialization.

This module is responsible for:
1. Initializing external service clients (Mistral, Pinecone)
2. Managing connections to these services
3. Providing a clean interface for other parts of the application

Separating client initialization into its own module:
- Makes it easier to swap out services (e.g., using a different embedding provider)
- Centralizes connection management
- Allows for better testing through dependency injection
"""

import os
from mistralai import Mistral
from pinecone import Pinecone
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

def init_mistral_client():
    """
    Initialize and return a Mistral client.
    
    Uses the API key from settings which is loaded from environment variables.
    
    Returns:
        Mistral: Initialized Mistral client
    
    Raises:
        ValueError: If the API key is missing
    """
    if not settings.MISTRAL_API_KEY:
        error_msg = "MISTRAL_API_KEY not found in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Initializing Mistral client")
    return Mistral(api_key=settings.MISTRAL_API_KEY)

def init_pinecone_client():
    """
    Initialize and return a Pinecone client.
    
    Returns:
        Pinecone: Initialized Pinecone client
    
    Raises:
        ValueError: If the API key is missing
    """
    if not settings.PINECONE_API_KEY:
        error_msg = "PINECONE_API_KEY not found in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Initializing Pinecone client")
    return Pinecone(api_key=settings.PINECONE_API_KEY)

def get_pinecone_index():
    """
    Get a specific Pinecone index.
    
    Returns:
        Index: The specific Pinecone index for this application
        
    Raises:
        ValueError: If index name is missing
    """
    if not settings.PINECONE_INDEX_NAME:
        error_msg = "PINECONE_INDEX_NAME not found in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    pc = init_pinecone_client()
    logger.info(f"Getting Pinecone index: {settings.PINECONE_INDEX_NAME}")
    return pc.Index(settings.PINECONE_INDEX_NAME)

# Initialize clients at module level for reuse (singleton pattern)
# Note: In production with high loads, consider a more sophisticated approach
# with connection pooling or lazy initialization
try:
    mistral_client = init_mistral_client()
    logger.info("Mistral client initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize Mistral client: {e}")
    mistral_client = None

# We don't pre-initialize Pinecone as it's more efficient to get the index when needed
