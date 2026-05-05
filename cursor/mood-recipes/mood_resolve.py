"""Resolve mood slug to a built-in template key for TheMealDB filters."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, UserMood
from recipe_service import VALID_MOODS


async def resolve_template_mood(session: AsyncSession, user: User | None, mood: str) -> str | None:
    key = mood.lower().strip()
    if key in VALID_MOODS:
        return key
    if user is None:
        return None
    result = await session.execute(
        select(UserMood).where(UserMood.user_id == user.id, UserMood.slug == key)
    )
    um = result.scalar_one_or_none()
    if um is None or um.template_mood not in VALID_MOODS:
        return None
    return um.template_mood
