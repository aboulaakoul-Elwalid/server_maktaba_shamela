from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from app.core.clients import appwrite_users, appwrite_account
from appwrite.exception import AppwriteException
import logging
import secrets
import time
from fastapi.responses import RedirectResponse
from app.config import settings
from typing import Optional
from app.api.auth_utils import get_current_user  # Import from new location
from fastapi.security import OAuth2PasswordBearer
logger = logging.getLogger(__name__)  # Add this

router = APIRouter(tags=["auth"])

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    """Response model for user profile information"""
    user_id: str
    email: str
    name: Optional[str] = None
    is_anonymous: bool = False

# Fix tokenUrl to match your actual endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/register", response_model=dict)
async def register(user: UserCreate):
    try:
        # Register user with Appwrite
        result = appwrite_users.create(
            user_id='unique()',
            email=user.email,
            password=user.password,
            name=user.name
        )
        
        return {"user_id": result["$id"], "message": "User registered successfully"}
    except AppwriteException as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    
    
@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    """Login user using Appwrite email/password session"""
    try:
        # Attempt to create a session using Appwrite
        # This verifies the email and password
        session = appwrite_account.create_email_password_session(
            email=user.email, 
            password=user.password
        )
    
        jwt_response = appwrite_account.create_jwt()
        jwt = jwt_response['jwt']
        
        logger.info(f"Successfully logged in user: {user.email}")
        
        # Return the JWT
        return {
            "access_token": jwt,
            "token_type": "bearer"
        }

    except AppwriteException as e:
        logger.error(f"Appwrite login error for {user.email}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {e.message}" # Use e.message for cleaner errors
        )
    except Exception as e:
        logger.error(f"Unexpected login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login."
        )

@router.get("/debug")
async def debug_appwrite():
    """Debug endpoint to check Appwrite methods"""
    try:
        import inspect

        methods = {
            "create_session": str(inspect.signature(appwrite_account.create_session)),
            "create_jwt": str(inspect.signature(appwrite_account.create_jwt)),
        }
        
        all_methods = [m for m in dir(appwrite_account) 
                     if not m.startswith('_') and callable(getattr(appwrite_account, m))]
        
        return {
            "available_methods": all_methods,
            "method_signatures": methods
        }
    except Exception as e:
        return {"error": str(e)}
    
@router.post("/anonymous", response_model=Token)
async def create_anonymous_session():
    """Create an Appwrite anonymous session and return a JWT"""
    try:
        # Create an anonymous session using Appwrite
        session = appwrite_account.create_anonymous_session()
        
        # Now that an anonymous session exists, create a JWT for it
        jwt_response = appwrite_account.create_jwt()
        jwt = jwt_response['jwt']
        
        # Optionally, log the Appwrite anonymous user ID if needed
        # anon_user = appwrite_account.get() # Get details if needed
        # logger.info(f"Created anonymous session for Appwrite user: {anon_user['$id']}")
        logger.info(f"Created anonymous session and JWT.")

        # Return the JWT
        return {
            "access_token": jwt,
            "token_type": "bearer"
        }
    except AppwriteException as e:
        logger.error(f"Appwrite anonymous session error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anonymous session creation failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected anonymous session error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during anonymous session creation."
        )
    
@router.get("/google")
async def google_auth_redirect():
    """Redirect to Google OAuth flow"""
    try:
        
        redirect_url = f"{settings.APPWRITE_ENDPOINT}/auth/oauth2/google/redirect"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Google auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Return the current authenticated user's profile information based on the validated token.
    """
    # The 'current_user' dict comes directly from the validated Appwrite user data
    # in get_current_user (auth_utils.py)
    return UserResponse(**current_user) # Directly pass the validated dict