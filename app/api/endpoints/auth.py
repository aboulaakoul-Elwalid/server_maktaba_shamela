from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.clients import appwrite_users, appwrite_account # Import appwrite_account
from appwrite.exception import AppwriteException
from fastapi.security import OAuth2PasswordBearer
from fastapi import status

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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/register", response_model=dict)
async def register(user: UserCreate):
    try:
        result = await appwrite_users.create(
            user_id='unique()',
            email=user.email,
            password=user.password,
            name=user.name
        )
        return {"user_id": result['$id'], "message": "User registered successfully"}
    except AppwriteException as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    try:
        session = await appwrite_account.create_email_session(user.email, user.password)
        jwt = await appwrite_account.create_jwt()
        return {"access_token": jwt['jwt'], "token_type": "bearer"}
    except AppwriteException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )