"""User favorite recipes."""

from __future__ import annotations

import json
from datetime import timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from dependencies import CurrentUser, SessionDep
from models import Favorite
from schemas import FavoriteCreate, FavoriteOut

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


def _favorite_to_out(f: Favorite) -> FavoriteOut:
    snap = None
    if f.snapshot_json:
        try:
            snap = json.loads(f.snapshot_json)
        except json.JSONDecodeError:
            snap = None
    created = f.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return FavoriteOut(
        id=f.id,
        meal_id=f.meal_id,
        mood_slug=f.mood_slug,
        snapshot=snap,
        created_at=created,
    )


@router.get("", response_model=list[FavoriteOut])
async def list_favorites(session: SessionDep, user: CurrentUser) -> list[FavoriteOut]:
    result = await session.execute(
        select(Favorite)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    )
    rows = result.scalars().all()
    return [_favorite_to_out(f) for f in rows]


@router.post("", response_model=FavoriteOut)
async def add_favorite(
    body: FavoriteCreate,
    session: SessionDep,
    user: CurrentUser,
) -> FavoriteOut:
    snap_json = json.dumps(body.snapshot) if body.snapshot else None
    result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.meal_id == body.meal_id.strip(),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.mood_slug = body.mood_slug.lower().strip()
        existing.snapshot_json = snap_json
        await session.commit()
        await session.refresh(existing)
        return _favorite_to_out(existing)

    fav = Favorite(
        user_id=user.id,
        meal_id=body.meal_id.strip(),
        mood_slug=body.mood_slug.lower().strip(),
        snapshot_json=snap_json,
    )
    session.add(fav)
    await session.commit()
    await session.refresh(fav)
    return _favorite_to_out(fav)


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(
    favorite_id: int,
    session: SessionDep,
    user: CurrentUser,
) -> None:
    res = await session.execute(
        delete(Favorite).where(Favorite.id == favorite_id, Favorite.user_id == user.id)
    )
    if res.rowcount == 0:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Favorite not found")
    await session.commit()
