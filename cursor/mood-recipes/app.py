"""Mood-based recipe app: static UI + API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from db import init_db
from dependencies import OptionalUser, SessionDep
from mood_resolve import resolve_template_mood
from recipe_service import VALID_MOODS, get_recipe_for_mood
from routers import auth, favorites, moods

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Mood Recipes", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(favorites.router)
app.include_router(moods.router)


@app.get("/api/recipe")
async def api_recipe(
    session: SessionDep,
    user: OptionalUser,
    mood: str = Query(..., description="Mood slug (built-in or your custom mood)"),
    exclude: str | None = Query(None, description="Comma-separated meal ids to avoid"),
):
    exclude_ids: set[str] = set()
    if exclude:
        exclude_ids = {x.strip() for x in exclude.split(",") if x.strip()}

    template = await resolve_template_mood(session, user, mood)
    if template is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mood. Valid built-ins: {', '.join(sorted(VALID_MOODS))}",
        )

    try:
        recipe = await get_recipe_for_mood(template, exclude_ids)
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"detail": "Recipe service unavailable.", "error": str(e)},
        )

    return recipe


@app.get("/login")
async def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/favorites")
async def favorites_page():
    return FileResponse(STATIC_DIR / "favorites.html")


app.mount(
    "/",
    StaticFiles(directory=str(STATIC_DIR), html=True),
    name="static",
)
