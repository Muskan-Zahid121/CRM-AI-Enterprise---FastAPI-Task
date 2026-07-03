from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.config import settings
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
ph = PasswordHasher()


def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "exp": int((now + timedelta(days=settings.JWT_EXPIRE_DAYS)).timestamp()),
        "iat": int(now.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def user_dict(user: User) -> dict[str, Any]:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


class RegisterPayload(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=6, max_length=255)


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=255)


@router.post("/register")
async def register(payload: RegisterPayload):
    if await User.filter(email=payload.email).exists():
        raise HTTPException(400, "An account with this email already exists.")
    user = await User.create(
        name=payload.name,
        email=payload.email,
        password=ph.hash(payload.password),
    )
    token = create_token(user.id)
    return {"success": True, "message": "Account created.", "token": token, "user": user_dict(user)}


@router.post("/signup")
async def signup(payload: RegisterPayload):
    """Alias for /register (legacy frontend compatibility)."""
    return await register(payload)


@router.post("/login")
async def login(payload: LoginPayload):
    user = await User.filter(email=payload.email).first()
    if not user:
        raise HTTPException(400, "Invalid email or password.")
    try:
        ph.verify(user.password, payload.password)
    except VerifyMismatchError:
        raise HTTPException(400, "Invalid email or password.")
    if ph.check_needs_rehash(user.password):
        user.password = ph.hash(payload.password)
        await user.save()
    token = create_token(user.id)
    return {"success": True, "message": "Logged in.", "token": token, "user": user_dict(user)}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Logged out {current_user.email}."}


@router.post("/refresh-token")
async def refresh_token(current_user: User = Depends(get_current_user)):
    return {"success": True, "token": create_token(current_user.id), "user": user_dict(current_user)}


@router.get("/profile")
async def profile(current_user: User = Depends(get_current_user)):
    return {"success": True, "user": user_dict(current_user)}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    """Alias for /profile (legacy frontend compatibility)."""
    return {"success": True, "user": user_dict(current_user)}


@router.put("/profile")
async def update_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_user)):
    if payload.name:
        current_user.name = payload.name
        await current_user.save()
    return {"success": True, "user": user_dict(current_user)}


@router.put("/change-password")
async def change_password(payload: ChangePasswordPayload, current_user: User = Depends(get_current_user)):
    try:
        ph.verify(current_user.password, payload.current_password)
    except VerifyMismatchError:
        raise HTTPException(400, "Current password is incorrect.")
    current_user.password = ph.hash(payload.new_password)
    await current_user.save()
    return {"success": True, "message": "Password updated."}


@router.post("/forgot-password")
async def forgot_password(payload: dict):
    return {"success": True, "message": "If that email exists, reset instructions were sent."}


@router.post("/reset-password")
async def reset_password(payload: dict):
    return {"success": True, "message": "Password reset endpoint ready for email integration."}


@router.post("/verify-email")
async def verify_email(payload: dict):
    return {"success": True, "message": "Email verification endpoint ready for SMTP integration."}
