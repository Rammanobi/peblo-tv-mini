
from pydantic import BaseModel, Field


class ShowCreate(BaseModel):
    title: str
    slug: str | None = None
    description: str | None = None
    category: str
    section: str | None = None
    status: str | None = "draft"


class ShowUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    description: str | None = None
    category: str | None = None
    section: str | None = None
    status: str | None = None


class SeasonCreate(BaseModel):
    season_number: int = Field(ge=0)
    title: str | None = None


class SeasonUpdate(BaseModel):
    title: str | None = None


class EpisodeCreate(BaseModel):
    title: str
    episode_number: int | None = None
    content_group: str
    language: str
    duration_seconds: int | None = None
    synopsis: str | None = None
    status: str | None = "draft"


class EpisodeUpdate(BaseModel):
    title: str | None = None
    episode_number: int | None = None
    content_group: str | None = None
    language: str | None = None
    duration_seconds: int | None = None
    synopsis: str | None = None
    status: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class PublishRequest(BaseModel):
    dry_run: bool = False
    note: str | None = None
