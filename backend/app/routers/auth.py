from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.deps import CurrentUser, get_current_user
from app.errors import ApiError
from app.models import User
from app.schemas import LoginRequest
from app.security import create_access_token, verify_password

router = APIRouter(tags=["auth"])


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role}


@router.post("/auth/login")
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise ApiError(401, "unauthorized", "Email or password is incorrect.")
    token, expires_in = create_access_token(user.id, user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user_out(user),
    }


@router.get("/auth/me")
async def me(current: CurrentUser = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.id == current.id))
    user = result.scalar_one()
    return user_out(user)
