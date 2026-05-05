"""Built-in and user-defined moods."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from dependencies import CurrentUser, OptionalUser, SessionDep
from models import UserMood
from recipe_service import BUILTIN_MOOD_LABELS, VALID_MOODS
from schemas import BuiltinMoodOut, MoodsResponse, UserMoodCreate, UserMoodOut

router = APIRouter(prefix="/api/moods", tags=["moods"])


def slugify_label(label: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", label.lower().strip())
    s = s.strip("-")
    return s or "mood"


@router.get("", response_model=MoodsResponse)
async def get_moods(session: SessionDep, user: OptionalUser) -> MoodsResponse:
    builtin = sorted(
        [BuiltinMoodOut(id=k, label=v) for k, v in BUILTIN_MOOD_LABELS.items()],
        key=lambda m: m.label.lower(),
    )
    custom: list[UserMoodOut] = []
    if user is not None:
        result = await session.execute(select(UserMood).where(UserMood.user_id == user.id))
        for um in result.scalars().all():
            custom.append(UserMoodOut(slug=um.slug, label=um.label, template_mood=um.template_mood))
        custom.sort(key=lambda m: m.label.lower())
    return MoodsResponse(builtin=builtin, custom=custom)


@router.post("", response_model=UserMoodOut)
async def create_user_mood(
    body: UserMoodCreate,
    session: SessionDep,
    user: CurrentUser,
) -> UserMoodOut:
    template = body.template_mood.lower().strip()
    if template not in VALID_MOODS:
        raise HTTPException(
            status_code=400,
            detail=f"template_mood must be one of: {', '.join(sorted(VALID_MOODS))}",
        )
    base_slug = slugify_label(body.label)
    slug = base_slug
    n = 2
    while True:
        result = await session.execute(
            select(UserMood).where(UserMood.user_id == user.id, UserMood.slug == slug)
        )
        if result.scalar_one_or_none() is None:
            break
        slug = f"{base_slug}-{n}"
        n += 1

    um = UserMood(
        user_id=user.id,
        slug=slug,
        label=body.label.strip(),
        template_mood=template,
    )
    session.add(um)
    await session.commit()
    await session.refresh(um)
    return UserMoodOut(slug=um.slug, label=um.label, template_mood=um.template_mood)
