from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import reference
from app.database import get_session
from app.deps import CurrentUser, require_editor
from app.errors import ApiError
from app.models import Artwork, Episode, Season, Show
from app.schemas import EpisodeCreate, EpisodeUpdate
from app.serializers import episode_dict
from app.utils import paginate_params

router = APIRouter(tags=["episodes"])


def _validate_enums(language=None, status=None):
    if language is not None and language not in reference.language_codes():
        raise ApiError(
            422,
            "validation_error",
            f'"{language}" is not a supported language.',
            [{"code": "ENUM_NOT_ALLOWED", "field": "language", "message": "See reference.json languages.", "hint": None, "resource": None}],
        )
    if status is not None and status not in reference.status_keys():
        raise ApiError(
            422,
            "validation_error",
            f'"{status}" is not a supported status.',
            [{"code": "ENUM_NOT_ALLOWED", "field": "status", "message": "See reference.json statuses.", "hint": None, "resource": None}],
        )


async def _check_trailer_rule(season: Season, episode_number, title, ep_id=None):
    if season.season_number == 0 and episode_number is not None:
        raise ApiError(
            422,
            "validation_error",
            "Trailers cannot have an episode number.",
            [
                {
                    "code": "TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER",
                    "field": "episode_number",
                    "message": "This episode is in season 0, which is reserved for trailers. Season 0 rows must leave episode_number empty.",
                    "hint": "Send episode_number: null, or move the episode to season 1 or later.",
                    "resource": {"type": "episode", "id": ep_id, "title": title},
                }
            ],
        )


async def _check_content_group_conflicts(session: AsyncSession, show_id: int, content_group: str, language: str, exclude_id=None):
    stmt = select(Episode).where(Episode.content_group == content_group)
    if exclude_id:
        stmt = stmt.where(Episode.id != exclude_id)
    rows = (await session.execute(stmt)).scalars().all()
    for r in rows:
        if r.show_id != show_id:
            raise ApiError(
                409,
                "conflict",
                f'Content group "{content_group}" already belongs to a different show.',
                [{"code": "CONTENT_GROUP_SINGLE_SHOW", "field": "content_group", "message": f'Content group "{content_group}" is used by show #{r.show_id}.', "hint": None, "resource": {"type": "episode", "id": r.id}}],
            )
        if r.language == language:
            raise ApiError(
                409,
                "conflict",
                f"There is already a {reference.language_label(language)} version of this episode.",
                [
                    {
                        "code": "CONTENT_GROUP_LANGUAGE_UNIQUE",
                        "field": "language",
                        "message": f'Episode #{r.id} ("{r.title}") already uses content group "{content_group}" with language "{language}". Each content group may have only one row per language.',
                        "hint": f"Edit episode #{r.id} instead, or give this row a different content_group.",
                        "resource": {"type": "episode", "id": r.id},
                    }
                ],
            )


async def _check_episode_number_unique(session: AsyncSession, season_id: int, episode_number, language: str, exclude_id=None):
    if episode_number is None:
        return
    stmt = select(Episode).where(Episode.season_id == season_id, Episode.episode_number == episode_number, Episode.language == language)
    if exclude_id:
        stmt = stmt.where(Episode.id != exclude_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        raise ApiError(
            409,
            "conflict",
            f"Episode {episode_number} already exists for this season and language.",
            [{"code": "EPISODE_NUMBER_UNIQUE_IN_SEASON", "field": "episode_number", "message": f"Episode #{existing.id} already uses episode_number {episode_number} in this season/language.", "hint": None, "resource": {"type": "episode", "id": existing.id}}],
        )


async def _check_publish_requirements(session: AsyncSession, ep: Episode, is_trailer: bool):
    problems = []
    if not is_trailer and (ep.duration_seconds is None or ep.duration_seconds <= 0):
        problems.append(
            {
                "code": "EPISODE_PUBLISHED_REQUIRES_DURATION",
                "field": "duration_seconds",
                "message": "Duration is missing. A published episode must have a duration greater than 0 seconds.",
                "hint": "Set duration_seconds on the episode before publishing.",
                "resource": {"type": "episode", "id": ep.id, "title": ep.title},
            }
        )
    arts = (await session.execute(select(Artwork).where(Artwork.owner_type == "episode", Artwork.owner_id == ep.id))).scalars().all()
    present = {a.kind for a in arts}
    missing = [k for k in reference.required_episode_kinds() if k not in present]
    if missing:
        problems.append(
            {
                "code": "EPISODE_PUBLISHED_REQUIRES_ARTWORK",
                "field": f"artwork.{missing[0]}",
                "message": f"A published episode needs poster, banner and thumbnail artwork. Missing: {', '.join(missing)}.",
                "hint": f"Upload via POST /episodes/{ep.id}/artwork with kind={missing[0]}, then publish again.",
                "resource": {"type": "episode", "id": ep.id, "title": ep.title},
            }
        )
    if problems:
        raise ApiError(
            422,
            "validation_error",
            f'"{ep.title}" cannot be published yet. {len(problems)} problem(s) must be fixed first.',
            problems,
        )


@router.get("/seasons/{season_id}/episodes")
async def list_episodes(
    season_id: int,
    language: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    season = (await session.execute(select(Season).where(Season.id == season_id))).scalar_one_or_none()
    if not season:
        raise ApiError(404, "not_found", f"Season #{season_id} was not found.")
    limit, offset = paginate_params(limit, offset)
    stmt = select(Episode).where(Episode.season_id == season_id)
    if language:
        stmt = stmt.where(Episode.language == language)
    if status:
        stmt = stmt.where(Episode.status == status)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await session.execute(stmt)).scalars().all()
    rows.sort(key=lambda e: (e.episode_number is not None, e.episode_number or 0, e.language))
    rows = rows[offset : offset + limit]
    artworks = (await session.execute(select(Artwork).where(Artwork.owner_type == "episode"))).scalars().all()
    items = [episode_dict(e, season.season_number, artworks) for e in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/seasons/{season_id}/episodes", status_code=201)
async def create_episode(season_id: int, payload: EpisodeCreate, user: CurrentUser = Depends(require_editor), session: AsyncSession = Depends(get_session)):
    season = (await session.execute(select(Season).where(Season.id == season_id))).scalar_one_or_none()
    if not season:
        raise ApiError(404, "not_found", f"Season #{season_id} was not found.")
    show = (await session.execute(select(Show).where(Show.id == season.show_id))).scalar_one()
    _validate_enums(language=payload.language, status=payload.status)
    await _check_trailer_rule(season, payload.episode_number, payload.title)
    await _check_content_group_conflicts(session, show.id, payload.content_group, payload.language)
    await _check_episode_number_unique(session, season_id, payload.episode_number, payload.language)

    ep = Episode(
        season_id=season_id,
        show_id=show.id,
        episode_number=payload.episode_number,
        title=payload.title,
        synopsis=payload.synopsis,
        content_group=payload.content_group,
        language=payload.language,
        duration_seconds=payload.duration_seconds,
        status=payload.status or "draft",
    )
    session.add(ep)
    await session.flush()
    if ep.status == "published":
        await _check_publish_requirements(session, ep, season.season_number == 0)
    await session.commit()
    return episode_dict(ep, season.season_number, [])


@router.get("/episodes/{episode_id}")
async def get_episode(episode_id: int, user: CurrentUser = Depends(require_editor), session: AsyncSession = Depends(get_session)):
    ep = (await session.execute(select(Episode).where(Episode.id == episode_id))).scalar_one_or_none()
    if not ep:
        raise ApiError(404, "not_found", f"Episode #{episode_id} was not found.")
    season = (await session.execute(select(Season).where(Season.id == ep.season_id))).scalar_one()
    artworks = (await session.execute(select(Artwork).where(Artwork.owner_type == "episode", Artwork.owner_id == episode_id))).scalars().all()
    out = episode_dict(ep, season.season_number, artworks)
    variants = (await session.execute(select(Episode).where(Episode.content_group == ep.content_group, Episode.id != ep.id))).scalars().all()
    out["variants"] = [{"id": v.id, "language": v.language, "title": v.title, "status": v.status} for v in variants]
    return out


@router.patch("/episodes/{episode_id}")
async def update_episode(episode_id: int, payload: EpisodeUpdate, user: CurrentUser = Depends(require_editor), session: AsyncSession = Depends(get_session)):
    ep = (await session.execute(select(Episode).where(Episode.id == episode_id))).scalar_one_or_none()
    if not ep:
        raise ApiError(404, "not_found", f"Episode #{episode_id} was not found.")
    season = (await session.execute(select(Season).where(Season.id == ep.season_id))).scalar_one()
    data = payload.model_dump(exclude_unset=True)
    _validate_enums(language=data.get("language"), status=data.get("status"))

    new_episode_number = data.get("episode_number", ep.episode_number)
    if "episode_number" in data or season.season_number == 0:
        await _check_trailer_rule(season, new_episode_number, ep.title, ep.id)

    if "content_group" in data or "language" in data:
        cg = data.get("content_group", ep.content_group)
        lang = data.get("language", ep.language)
        await _check_content_group_conflicts(session, ep.show_id, cg, lang, exclude_id=ep.id)

    if "episode_number" in data:
        lang = data.get("language", ep.language)
        await _check_episode_number_unique(session, ep.season_id, new_episode_number, lang, exclude_id=ep.id)

    for field, value in data.items():
        setattr(ep, field, value)
    await session.flush()
    if ep.status == "published":
        await _check_publish_requirements(session, ep, season.season_number == 0)
    await session.commit()
    artworks = (await session.execute(select(Artwork).where(Artwork.owner_type == "episode", Artwork.owner_id == episode_id))).scalars().all()
    return episode_dict(ep, season.season_number, artworks)


@router.delete("/episodes/{episode_id}", status_code=204)
async def delete_episode(episode_id: int, user: CurrentUser = Depends(require_editor), session: AsyncSession = Depends(get_session)):
    ep = (await session.execute(select(Episode).where(Episode.id == episode_id))).scalar_one_or_none()
    if not ep:
        raise ApiError(404, "not_found", f"Episode #{episode_id} was not found.")
    await session.delete(ep)
    await session.commit()
    return None
