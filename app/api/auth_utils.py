from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from appwrite.services.account import Account
from appwrite.exception import AppwriteException
from app.core.clients import get_user_client
import logging
from typing import Dict, Optional
import secrets
from pydantic import BaseModel, EmailStr # Import BaseModel and EmailStr

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# --- Define the UserResponse Model ---
class UserResponse(BaseModel):
    """Pydantic model for user profile response."""
    user_id: str
    email: Optional[EmailStr] = None # Email is optional for anonymous users
    name: Optional[str] = None
    is_anonymous: bool = False
    registration: Optional[str] = None # Assuming registration is a string timestamp
    prefs: Dict = {} # User preferences

    class Config:
        from_attributes = True # Allows creating model from dict/object attributes


# --- Update get_current_user ---
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserResponse: # Changed return type hint
    """
    Validate the JWT using Appwrite via a user-scoped client and return the user data
    as a UserResponse model. Requires authentication.
    """
    if token is None:
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
        # 1. Get a user-scoped client using the token
        user_client = get_user_client(jwt=token) # Factory handles client setup and JWT setting

        # 2. Create an Account service instance from the user client
        account = Account(user_client)

        # 3. Verify the token by fetching the user account
        user_data = account.get() # This call uses the JWT set on user_client

        # 4. Create and return a UserResponse instance
        profile_data = {
            "user_id": user_data['$id'],
            "email": user_data.get('email'),
            "name": user_data.get('name'),
            "is_anonymous": not bool(user_data.get('email')), # Determine anonymity
            "registration": user_data.get('$registration'),
            "prefs": user_data.get('prefs', {})
        }
        logger.debug(f"Token validated for user: {profile_data['user_id']}, Anonymous: {profile_data['is_anonymous']}")
        return UserResponse(**profile_data) # Return model instance

    except AppwriteException as e:
        logger.error(f"Appwrite token validation error: {e.message} (Code: {e.code}, Type: {e.type})")
        if e.code == 401:
             raise credentials_exception from e
        else:
             raise HTTPException(
                 status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                 detail=f"Authentication service error: {e.message}"
             ) from e
    except HTTPException as e:
        logger.error(f"HTTP Exception during user client creation: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication."
        ) from e

# --- Update get_user_or_anonymous ---
async def get_user_or_anonymous(token: Optional[str] = Depends(oauth2_scheme)) -> UserResponse: # Changed return type hint
    """
    Returns authenticated user data if a valid token is provided,
    otherwise returns a default anonymous user structure as a UserResponse model.
    """
    if token:
        try:
            return await get_current_user(token)
        except HTTPException as e:
            if e.status_code == status.HTTP_401_UNAUTHORIZED:
                 logger.debug(f"Invalid token provided, treating as anonymous.")
            elif e.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                 logger.warning(f"Auth service unavailable ({e.detail}), treating as anonymous.")
            else:
                 logger.warning(f"Token validation failed (Status: {e.status_code}, Detail: {e.detail}). Treating as anonymous.")

    # Generate anonymous user structure
    anon_id = f"anon_{secrets.token_hex(8)}"
    logger.debug(f"No valid token found or validation failed, returning anonymous user structure (ID: {anon_id})")
    anon_data = {
        "user_id": anon_id,
        "email": None,
        "name": "Anonymous User",
        "is_anonymous": True,
        "registration": None,
        "prefs": {}
    }
    return UserResponse(**anon_data) # Return model instance