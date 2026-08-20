from typing import Any, Optional

from pydantic import BaseModel, Field


class ShowCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    category: str
    section: Optional[str] = None
    status: Optional[str] = "draft"


class ShowUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    section: Optional[str] = None
    status: Optional[str] = None


class SeasonCreate(BaseModel):
    season_number: int = Field(ge=0)
    title: Optional[str] = None


class SeasonUpdate(BaseModel):
    title: Optional[str] = None


class EpisodeCreate(BaseModel):
    title: str
    episode_number: Optional[int] = None
    content_group: str
    language: str
    duration_seconds: Optional[int] = None
    synopsis: Optional[str] = None
    status: Optional[str] = "draft"


class EpisodeUpdate(BaseModel):
    title: Optional[str] = None
    episode_number: Optional[int] = None
    content_group: Optional[str] = None
    language: Optional[str] = None
    duration_seconds: Optional[int] = None
    synopsis: Optional[str] = None
    status: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class PublishRequest(BaseModel):
    dry_run: bool = False
    note: Optional[str] = None
