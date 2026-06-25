from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.database import get_user_by_username, update_user_password
from app.db.session import get_async_session
from app.models import LoginRequest, LoginResponse, ResetPasswordRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
) -> LoginResponse:
    user = await get_user_by_username(session, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user.id, user.username, user.role)
    return LoginResponse(
        token=token,
        user=UserOut(id=user.id, username=user.username, role=user.role),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut(id=current_user["id"], username=current_user["username"], role=current_user["role"])


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    target = await get_user_by_username(session, body.target_username)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    await update_user_password(session, target.id, hash_password(body.new_password))
    await session.commit()

    return {"message": f"Password updated for user '{body.target_username}'"}
