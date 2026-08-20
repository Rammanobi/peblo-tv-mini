from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.errors import ApiError
from app.models import User
from app.security import decode_token


class CurrentUser:
    def __init__(self, id: int, email: str, role: str):
        self.id = id
        self.email = email
        self.role = role


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Missing or invalid authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    claims = decode_token(token)
    if not claims:
        raise ApiError(401, "unauthorized", "The access token is invalid or expired.")
    user_id = int(claims["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ApiError(401, "unauthorized", "The access token no longer matches a known user.")
    return CurrentUser(id=user.id, email=user.email, role=user.role)


def require_role(*roles: str):
    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ApiError(
                403,
                "forbidden",
                f"This action requires one of the following roles: {', '.join(roles)}.",
            )
        return user

    return checker


require_editor = require_role("editor", "admin")
require_admin = require_role("admin")
