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
from appwrite.services.databases import Databases
from appwrite.services.account import Account
from appwrite.exception import AppwriteException
from fastapi import Depends, HTTPException, status, Request

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
    Initializes and returns the Pinecone index client.
    """
    if not settings.PINECONE_INDEX_NAME:
        error_msg = "PINECONE_INDEX_NAME not found in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    pc = init_pinecone_client()
    logger.info(f"Getting Pinecone index: {settings.PINECONE_INDEX_NAME}")
    return pc.Index(settings.PINECONE_INDEX_NAME)

# --- Base Client Initialization ---

def _initialize_appwrite_client() -> Client:
    """Creates and configures a base Appwrite client instance."""
    client = Client()
    client.set_endpoint(settings.APPWRITE_ENDPOINT)
    client.set_project(settings.APPWRITE_PROJECT_ID)
    return client

# --- Admin Client (API Key Auth) ---

def get_admin_client() -> Client:
    """
    Returns an Appwrite client authenticated with the admin API key.
    Used for server-side operations requiring admin privileges.
    """
    client = _initialize_appwrite_client()
    try:
        client.set_key(settings.APPWRITE_API_KEY)
        logger.debug("Admin Appwrite client initialized with API Key.")
        return client
    except Exception as e: # Catch potential errors during key setting
        logger.error(f"Failed to initialize admin client with API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure admin authentication service."
        )

# --- User Client (JWT Auth) ---

def get_user_client(jwt: str) -> Client:
    """
    Returns an Appwrite client authenticated with a user's JWT.
    Used for operations performed on behalf of a specific user.

    Args:
        jwt: The user's JSON Web Token.

    Raises:
        HTTPException: If JWT is missing or client setup fails.
    """
    if not jwt:
        # This case should ideally be caught by Depends(oauth2_scheme) earlier
        logger.error("Attempted to get user client without providing a JWT.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing."
        )

    client = _initialize_appwrite_client()
    try:
        client.set_jwt(jwt)
        logger.debug("User Appwrite client initialized with JWT.")
        return client
    except Exception as e: # Catch potential errors during JWT setting
        logger.error(f"Failed to initialize user client with JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure user authentication service."
        )

# --- Service Dependencies ---

def get_admin_users_service() -> Users:
    """Dependency to get an admin-authenticated Users service."""
    admin_client = get_admin_client()
    return Users(admin_client)

def get_admin_account_service() -> Account:
    """Dependency to get an admin-authenticated Account service."""
    admin_client = get_admin_client()
    return Account(admin_client)

async def get_admin_db_service(client: Client = Depends(get_admin_client)) -> Databases:
    """Dependency to get a Databases service instance using the admin client."""
    return Databases(client)

# Dependency for user-scoped Account service - Requires a valid token
# This will be used by get_current_user internally now.
# We don't directly inject this into endpoints often, as get_current_user handles it.
async def get_user_account_service_from_token(token: str) -> Account:
    """
    Creates an Account service instance using a provided user JWT.
    Used internally by authentication utilities.
    """
    if not token:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not provided")
    try:
        user_client = get_user_client(jwt=token) # Use the factory
        return Account(user_client)
    except ValueError as e: # Catch the ValueError from get_user_client if token is empty
         logger.error(f"Value error creating user client for token: {e}")
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token provided")
    except HTTPException as e: # Propagate HTTP exceptions from get_user_client
        raise e
    except Exception as e:
        logger.error(f"Unexpected error creating user account service from token: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error setting up user context")