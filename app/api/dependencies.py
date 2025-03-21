# app/api/dependencies.py
"""
API dependencies module.

This module defines reusable dependencies for FastAPI endpoints using
its dependency injection system. Dependencies can be used to:
1. Share common functionality across endpoints
2. Implement middleware-like behavior for requests
3. Set up and tear down resources for endpoints

Benefits of FastAPI's dependency injection:
- Promotes code reuse
- Simplifies testing through mocking
- Clarifies endpoint requirements
- Handles errors consistently
"""

from fastapi import Depends, Header, HTTPException, status
from typing import Optional, List
import secrets
import time

from app.config.settings import settings, Settings
from app.core.clients import get_pinecone_index
from pinecone import Pinecone

# Simple in-memory API key store with rate limiting
# In production, use a database or auth service
API_KEYS = {
    "test-key": {
        "name": "Test API Key",
        "rate_limit": 59,  # requests per minute
        "calls": {},  # timestamp -> count
    }
}

def get_settings():
    """
    Dependency for accessing application settings.
    
    While we have a global settings object, providing it through a dependency
    makes testing easier by allowing it to be overridden in tests.
    
    Returns:
        Settings: Application settings
    """
    return settings

def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    Validate the API key and enforce rate limits.
    
    Args:
        api_key: The API key from the request header
        
    Raises:
        HTTPException: If the API key is invalid or rate limited
    """
    # Skip validation if not required
    if not settings.API_KEY_REQUIRED:
        return True
        
    # Check if API key is provided
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    
    # Check if API key is valid
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Enforce rate limiting
    key_data = API_KEYS[api_key]
    current_min = int(time.time() / 60)
    
    # Clean up old entries
    key_data["calls"] = {ts: count for ts, count in key_data["calls"].items() 
                         if ts >= current_min - 10}  # Keep last 10 minutes
    
    # Check and update rate limit
    current_count = key_data["calls"].get(current_min, 0)
    if current_count >= key_data["rate_limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Update count
    key_data["calls"][current_min] = current_count + 1
    
    return True

def get_pinecone_client():
    """
    Dependency for accessing the Pinecone client.
    
    Returns:
        Pinecone client instance
        
    Raises:
        HTTPException: If the client cannot be initialized
    """
    try:
        return get_pinecone_index()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to vector database: {str(e)}"
        )