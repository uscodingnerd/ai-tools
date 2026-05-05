"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import get_session
from models import User
from security import decode_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    access_token: str | None = Cookie(None, alias=settings.cookie_name),
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    sub = decode_token(access_token)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    try:
        user_id = int(sub)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_optional(
    session: SessionDep,
    access_token: str | None = Cookie(None, alias=settings.cookie_name),
) -> User | None:
    if not access_token:
        return None
    sub = decode_token(access_token)
    if sub is None:
        return None
    try:
        user_id = int(sub)
    except ValueError:
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
