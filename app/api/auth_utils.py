from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from appwrite.client import Client # Assuming get_appwrite_client returns this type
from appwrite.services.account import Account # <-- Add this import
from appwrite.exception import AppwriteException
from app.core.clients import get_appwrite_client # Assuming you have a way to get a client instance
import logging
from typing import Dict, Optional
import secrets
# ... rest of the file

logger = logging.getLogger(__name__)

# OAuth2 scheme for token handling (expects Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False) # auto_error=False allows optional auth

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Dict:
    """
    Validate the JWT using Appwrite and return the user data.
    Handles both authenticated and potentially anonymous users if a token is present.
    """
    if token is None:
         # This case might be handled by get_user_or_anonymous if needed,
         # or raise error if auth is strictly required.
         # For now, let's assume endpoints using this strictly require auth.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Get a fresh Appwrite client instance for this request
        # Important: Do NOT reuse the admin client directly if it has admin privileges set.
        # Create a client instance specifically for validating the user's JWT.
        client = get_appwrite_client(is_admin=False) # Need a way to get a non-admin client
        account = Account(client)

        # Set the JWT for this client instance. This tells the SDK to use the user's token.
        client.set_jwt(token)

        # Verify the token by fetching the user account associated with it
        user_data = account.get()

        # Extract relevant details (adjust keys based on Appwrite response)
        # Check if the user has an email - if not, likely anonymous
        is_anonymous = not user_data.get('email') 
        
        profile = {
            "user_id": user_data['$id'],
            "email": user_data.get('email'), # Use .get() for optional fields
            "name": user_data.get('name'),
            "is_anonymous": is_anonymous
            # Add any other fields you need from the Appwrite user object
        }
        logger.debug(f"Token validated for user: {profile['user_id']}, Anonymous: {is_anonymous}")
        return profile

    except AppwriteException as e:
        # Handle specific Appwrite errors, e.g., invalid token, expired session
        logger.error(f"Appwrite token validation error: {e.message} (Code: {e.code}, Type: {e.type})")
        # You might want different status codes based on e.code or e.type
        # For example, 401 for invalid token, maybe 403 if permissions fail later
        raise credentials_exception from e
    except Exception as e:
        # Catch unexpected errors during validation
        logger.error(f"Unexpected error during token validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication."
        ) from e

# You might also need a dependency for endpoints allowing EITHER authenticated OR anonymous users
async def get_user_or_anonymous(token: Optional[str] = Depends(oauth2_scheme)) -> Dict:
    """
    Returns authenticated user data if a valid token is provided,
    otherwise returns a default anonymous user structure.
    """
    if token:
        try:
            # Reuse the main validation logic
            return await get_current_user(token)
        except HTTPException as e:
            # If token is present but invalid (401), re-raise
            if e.status_code == status.HTTP_401_UNAUTHORIZED:
                 raise e
            # Handle other potential errors from get_current_user if needed,
            # or fall through to anonymous
            logger.warning(f"Token provided but validation failed (non-401): {e.detail}. Treating as anonymous.")

    # If no token or validation failed in a non-critical way, return anonymous structure
    # Note: This anonymous user doesn't have a real Appwrite session unless
    # the client explicitly called /anonymous first. This dependency just provides
    # a consistent structure for endpoints that allow unauthenticated access.
    return {
        "user_id": f"anon_{secrets.token_hex(8)}", # Generate a temporary ID
        "email": None,
        "name": "Anonymous User",
        "is_anonymous": True
    }