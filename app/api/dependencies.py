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

from fastapi import Depends, Header, HTTPException, status, Request
from typing import Optional, List, Dict
import secrets
import time
import logging

from app.config.settings import settings, Settings
from app.core.clients import get_pinecone_index
from app.api.auth_utils import get_current_user, get_user_or_anonymous

logger = logging.getLogger(__name__)

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

# Simple in-memory rate limiter
# In production, consider using Redis for distributed rate limiting
class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.user_requests: Dict[str, Dict] = {}
        
    def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if a user has exceeded their rate limit
        
        Args:
            user_id: The user's ID or IP address
            
        Returns:
            bool: True if request is allowed, False if rate limited
        """
        current_time = int(time.time())
        current_minute = current_time // 60
        
        # Initialize user data if not exists
        if user_id not in self.user_requests:
            self.user_requests[user_id] = {"minute": current_minute, "count": 0}
            
        user_data = self.user_requests[user_id]
        
        # Reset counter if we're in a new minute
        if user_data["minute"] != current_minute:
            user_data["minute"] = current_minute
            user_data["count"] = 0
            
        # Check if user has exceeded rate limit
        if user_data["count"] >= self.requests_per_minute:
            return False
            
        # Increment counter and allow request
        user_data["count"] += 1
        return True

# Create a global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=30)

# This dependency now correctly uses the imported get_user_or_anonymous
async def check_rate_limit(user: dict = Depends(get_user_or_anonymous)):
    """
    Dependency to enforce rate limits on API endpoints
    
    Args:
        user: The authenticated user (or anonymous) from auth_utils
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    # Use user_id from the validated user data (Appwrite ID or generated anonymous ID)
    user_id = user.get("user_id", f"fallback_anon_{secrets.token_hex(4)}") # Added fallback just in case
    
    if not rate_limiter.check_rate_limit(user_id):
        logger.warning(f"Rate limit exceeded for user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    return True

# Now use this in your chat endpoints
# For example:
# @router.post("/messages", dependencies=[Depends(check_rate_limit)])