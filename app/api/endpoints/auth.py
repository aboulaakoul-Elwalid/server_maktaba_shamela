from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, EmailStr
# Import specific service dependencies from your clients module
from app.core.clients import get_admin_users_service, get_admin_account_service
from appwrite.services.users import Users
from appwrite.services.account import Account
from appwrite.exception import AppwriteException
import logging
import time
from fastapi.responses import JSONResponse
from app.config import settings
from typing import Dict, Optional
# Import authentication utilities and the scheme
from app.api.auth_utils import oauth2_scheme, UserResponse, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# --- Pydantic Models ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    issued_at: int

# --- Endpoints ---

@router.post("/register", response_model=Dict[str, str])
async def register_user(
    user_data: UserCreate,
    admin_users: Users = Depends(get_admin_users_service)
):
    """Registers a new user using admin privileges."""
    try:
        user = admin_users.create(
            user_id='unique()',
            email=user_data.email,
            password=user_data.password,
            name=user_data.name
        )
        logger.info(f"User registered successfully: {user_data.email}, ID: {user['$id']}")
        return {"user_id": user['$id'], "message": "User registered successfully"}
    except AppwriteException as e:
        logger.error(f"Appwrite registration error for {user_data.email}: {e.message} (Code: {e.code}, Type: {e.type})")
        if e.code == 409: # User already exists
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
        elif e.code == 400: # Bad request (e.g., invalid password format)
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Registration failed: {e.message}")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred during registration.")
    except Exception as e:
        logger.exception(f"Unexpected error during registration for {user_data.email}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: UserLogin,
    admin_account: Account = Depends(get_admin_account_service),
    admin_users: Users = Depends(get_admin_users_service) # Add dependency for admin_users
):
    """Logs in a user and returns a JWT."""
    user_id = None
    try:
        # 1. Verify credentials by attempting to create a session
        # We don't need the session object itself, just need to know if it succeeds
        session = admin_account.create_email_password_session(
            email=form_data.email,
            password=form_data.password
        )
        user_id = session['userId'] # Get user ID from the successful session creation
        logger.info(f"Password verified for user: {form_data.email}, User ID: {user_id}")

        # 2. If verification successful, create JWT using admin_users service
        # This requires the API key to have 'users.write' scope
        jwt_creation_time = int(time.time())
        jwt_result = admin_users.create_jwt(user_id=user_id) # Default duration
        jwt = jwt_result['jwt']

        # Calculate expiry (Appwrite default JWT expiry is 15 mins, but create_jwt might differ - check docs or decode)
        # Assuming a default expiry, e.g., 1 hour for simplicity here. Adjust as needed.
        expires_in = 3600 # Example: 1 hour in seconds

        logger.info(f"JWT created successfully for user: {form_data.email}")
        return Token(
            access_token=jwt,
            token_type="bearer",
            expires_in=expires_in,
            issued_at=jwt_creation_time
        )

    except AppwriteException as e:
        logger.error(f"Appwrite login error for {form_data.email}: {e.message} (Code: {e.code}, Type: {e.type})")
        # Handle credential errors specifically from create_email_password_session
        if e.code == 401 and e.type == 'user_invalid_credentials':
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Handle potential errors from create_jwt (though less likely with just user_id)
        elif e.code == 404 and e.type == 'user_not_found':
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found after successful login attempt (internal inconsistency).")
        else:
            # Catch-all for other Appwrite errors during login/JWT creation
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Appwrite service error: {e.message}")

    except Exception as e:
        logger.exception(f"Unexpected error during login for {form_data.email}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during login.")


# --- /me endpoint (should remain the same, using auth_utils.get_current_user) ---
@router.get("/me", response_model=UserResponse) # Make sure UserResponse is correctly defined/imported
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    """Fetches the profile of the currently authenticated user."""
    # get_current_user dependency handles JWT validation and fetching user data
    return current_user

