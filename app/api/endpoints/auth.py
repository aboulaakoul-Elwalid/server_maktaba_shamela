from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.clients import appwrite_users, appwrite_account
from appwrite.exception import AppwriteException
from fastapi.security import OAuth2PasswordBearer
from fastapi import status
import logging  # Add this missing import
import secrets
import time

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

# Fix tokenUrl to match your actual endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Simple in-memory session store
# In production, use Redis or a database
SESSIONS = {}  # token -> {user_id, expires_at}

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
    """Simple email/password login"""
    try:
        # Simplify this to avoid Appwrite query issues
        try:
            # Generate a user ID (this is just for testing)
            user_id = f"user_{user.email.split('@')[0]}"
            
            # Generate a secure random token
            token = secrets.token_hex(16)
            
            # Store in our session store with 24 hour expiry
            SESSIONS[token] = {
                "user_id": user_id,
                "expires_at": time.time() + 86400  # 24 hours
            }
            
            # Print for debugging
            print(f"Created session token: {token} for user: {user_id}")
            print(f"Current sessions: {SESSIONS}")
            
            # Return the token
            return {
                "access_token": token,
                "token_type": "bearer"
            }
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Login error: {str(e)}"
            )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
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