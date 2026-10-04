from pydantic import BaseModel
from fastapi import APIRouter, Depends

from backend.app.core.auth import (
    get_user_by_email,
    verify_password,
    create_access_token,
    get_current_user,
    require_role
)
from backend.app.core.errors import AppException

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    role: str
    preferred_lang: str

class LoginResponse(BaseModel):
    token: str
    user: UserProfile

class MeResponse(BaseModel):
    user: UserProfile

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise AppException(
            code="NOT_AUTHENTICATED",
            message="Invalid email or password.",
            status_code=401
        )
    
    token = create_access_token({"sub": user["id"], "role": user["role"], "email": user["email"]})
    return LoginResponse(
        token=token,
        user=UserProfile(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            preferred_lang=user.get("preferred_lang") or "en"
        )
    )

@router.get("/me", response_model=MeResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return MeResponse(
        user=UserProfile(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            preferred_lang=user.get("preferred_lang") or "en"
        )
    )
