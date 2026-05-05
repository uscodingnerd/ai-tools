"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=128)


class FavoriteCreate(BaseModel):
    meal_id: str = Field(max_length=32)
    mood_slug: str = Field(max_length=64)
    snapshot: dict | None = None


class FavoriteOut(BaseModel):
    id: int
    meal_id: str
    mood_slug: str
    snapshot: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserMoodCreate(BaseModel):
    label: str = Field(min_length=1, max_length=128)
    template_mood: str = Field(max_length=64)


class UserMoodOut(BaseModel):
    slug: str
    label: str
    template_mood: str

    model_config = {"from_attributes": True}


class BuiltinMoodOut(BaseModel):
    id: str
    label: str


class MoodsResponse(BaseModel):
    builtin: list[BuiltinMoodOut]
    custom: list[UserMoodOut]
