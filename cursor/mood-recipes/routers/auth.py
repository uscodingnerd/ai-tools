"""Authentication routes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import aiosmtplib
from email.message import EmailMessage
from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config import settings
from dependencies import CurrentUser, SessionDep
from models import PasswordResetToken, User
from schemas import (
    ForgotPasswordBody,
    LoginBody,
    RegisterBody,
    ResetPasswordBody,
    UserPublic,
)
from security import create_access_token, hash_password, hash_reset_token, new_reset_token, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic)
async def register(body: RegisterBody, session: SessionDep) -> UserPublic:
    user = User(email=body.email.lower().strip(), hashed_password=hash_password(body.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    await session.refresh(user)
    return UserPublic.model_validate(user)


@router.post("/login")
async def login(body: LoginBody, session: SessionDep, response: Response) -> UserPublic:
    result = await session.execute(select(User).where(User.email == body.email.lower().strip()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user.id))
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return UserPublic.model_validate(user)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key=settings.cookie_name, path="/")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserPublic)
async def me(user: CurrentUser) -> User:
    return user


async def _send_reset_email(to_email: str, reset_link: str) -> None:
    if not settings.smtp_host or not settings.smtp_from:
        return
    msg = EmailMessage()
    msg["Subject"] = "Reset your Mood Recipes password"
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(f"Reset your password using this link (valid for {settings.reset_token_expire_minutes} minutes):\n\n{reset_link}")
    kwargs: dict = {
        "hostname": settings.smtp_host,
        "port": settings.smtp_port,
    }
    if settings.smtp_user:
        kwargs["username"] = settings.smtp_user
        kwargs["password"] = settings.smtp_password or ""
        kwargs["start_tls"] = True
    await aiosmtplib.send(msg, **kwargs)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordBody, session: SessionDep) -> dict:
    result = await session.execute(select(User).where(User.email == body.email.lower().strip()))
    user = result.scalar_one_or_none()
    out: dict = {"detail": "If that email is registered, you will receive reset instructions."}
    if user is None:
        return out

    raw = new_reset_token()
    th = hash_reset_token(raw)
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_expire_minutes)
    session.add(PasswordResetToken(user_id=user.id, token_hash=th, expires_at=expires))
    await session.commit()

    reset_link = f"{settings.public_base_url.rstrip('/')}/reset-password.html?token={raw}"
    if settings.smtp_host and settings.smtp_from:
        try:
            await _send_reset_email(user.email, reset_link)
        except Exception as e:
            logger.exception("Failed to send reset email: %s", e)
    if settings.debug:
        out["reset_token"] = raw
        out["reset_link"] = reset_link
    return out


@router.post("/reset-password")
async def reset_password(body: ResetPasswordBody, session: SessionDep) -> dict[str, str]:
    th = hash_reset_token(body.token.strip())
    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == th,
            PasswordResetToken.used_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    ures = await session.execute(select(User).where(User.id == row.user_id))
    user = ures.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")

    user.hashed_password = hash_password(body.new_password)
    row.used_at = now
    await session.commit()
    return {"detail": "Password updated. You can log in now."}
