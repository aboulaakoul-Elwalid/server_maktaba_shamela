from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import time
from typing import Dict, Optional
from app.api.endpoints.auth import SESSIONS  # This is now safe to import

# OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    """Validate the access token and return the user data"""
    if token not in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
        
    session = SESSIONS[token]
    
    # Check if token has expired
    if session["expires_at"] < time.time():
        # Remove expired session
        SESSIONS.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    
    # Return user information
    return {
        "user_id": session["user_id"],
        "is_anonymous": session.get("is_anonymous", False)
    }

class OAuth2PasswordBearerOptional(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        try:
            return await super().__call__(request)
        except HTTPException:
            return None