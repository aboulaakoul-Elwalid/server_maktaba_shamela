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
from appwrite.client import Client
from appwrite.services.users import Users
from appwrite.services.databases import Databases  # Corrected import
from appwrite.services.account import Account # Import Account service

logger = logging.getLogger(__name__)

def init_mistral_client():
    """Initialize and return a Mistral client."""
    if not settings.MISTRAL_API_KEY:
        error_msg = "MISTRAL_API_KEY not found in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        from mistralai.client import MistralClient
        logger.info("Initializing Mistral client")
        return MistralClient(api_key=settings.MISTRAL_API_KEY)
    except ImportError:
        logger.error("mistralai package not installed. Install with: pip install mistralai")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Mistral client: {str(e)}")
        return None

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
# Initialize Appwrite client
def get_appwrite_client():
    """
    Initialize and return an Appwrite client.
    
    Uses the credentials from settings which are loaded from environment variables.
    
    Returns:
        Client: Initialized Appwrite client
    
    Raises:
        ValueError: If required credentials are missing
    """
    if not settings.APPWRITE_ENDPOINT:
        error_msg = "APPWRITE_ENDPOINT not found in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    if not settings.APPWRITE_PROJECT_ID:
        error_msg = "APPWRITE_PROJECT_ID not found in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    if not settings.APPWRITE_API_KEY:
        error_msg = "APPWRITE_API_KEY not found in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Initializing Appwrite client")
    client = Client()
    client.set_endpoint(settings.APPWRITE_ENDPOINT)
    client.set_project(settings.APPWRITE_PROJECT_ID)
    client.set_key(settings.APPWRITE_API_KEY)
    return client

# Services
try:
    appwrite_client = get_appwrite_client()
    appwrite_users = Users(appwrite_client)
    appwrite_db = Databases(appwrite_client)  # Corrected class name
    appwrite_account = Account(appwrite_client) # Initialize Account service
    logger.info("Appwrite client initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize Appwrite client: {e}")
    appwrite_client = None
    appwrite_users = None
    appwrite_db = None
    appwrite_account = None