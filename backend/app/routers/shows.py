from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import reference
from app.database import get_session
from app.deps import CurrentUser, require_admin, require_editor
from app.errors import ApiError
from app.models import Artwork, Episode, Season, Show
from app.schemas import ShowCreate, ShowUpdate
from app.serializers import show_dict
from app.services.publish import get_last_successful_run
from app.utils import paginate_params, slugify

router = APIRouter(tags=["shows"])


async def _counts_for_show(session: AsyncSession, show_id: int):
    seasons = (await session.execute(select(Season).where(Season.show_id == show_id))).scalars().all()
    real_seasons = [s for s in seasons if s.season_number != 0]
    episodes = (await session.execute(select(Episode).where(Episode.show_id == show_id))).scalars().all()
    season_ids_trailer = {s.id for s in seasons if s.season_number == 0}
    ep_count = sum(1 for e in episodes if e.season_id not in season_ids_trailer)
    trailer_count = sum(1 for e in episodes if e.season_id in season_ids_trailer)
    return len(real_seasons), ep_count, trailer_count


def _validate_enums(category=None, section=None, status=None):
    if category is not None and category not in reference.category_keys():
        raise ApiError(
            422,
            "validation_error",
            f'"{category}" is not a supported category.',
            [
                {
                    "code": "ENUM_NOT_ALLOWED",
                    "field": "category",
                    "message": "See reference.json categories.",
                    "hint": None,
                    "resource": None,
                }
            ],
        )
    if section is not None and section not in reference.section_keys():
        raise ApiError(
            422,
            "validation_error",
            f'"{section}" is not a supported section.',
            [
                {
                    "code": "ENUM_NOT_ALLOWED",
                    "field": "section",
                    "message": "See reference.json sections.",
                    "hint": None,
                    "resource": None,
                }
            ],
        )
    if status is not None and status not in reference.status_keys():
        raise ApiError(
            422,
            "validation_error",
            f'"{status}" is not a supported status.',
            [
                {
                    "code": "ENUM_NOT_ALLOWED",
                    "field": "status",
                    "message": "See reference.json statuses.",
                    "hint": None,
                    "resource": None,
                }
            ],
        )


async def _check_publish_requirements(session: AsyncSession, show: Show):
    problems = []
    if not show.section:
        problems.append(
            {
                "code": "SHOW_PUBLISHED_REQUIRES_SECTION",
                "field": "section",
                "message": "A published show must belong to a section. Choose one of: "
                + ", ".join(s["label"] for s in reference.nav_sections()) + ".",
                "hint": f'PATCH /shows/{show.id} with {{"section": "learning"}}.',
                "resource": {"type": "show", "id": show.id, "title": show.title},
            }
        )
    arts = (
        await session.execute(
            select(Artwork).where(Artwork.owner_type == "show", Artwork.owner_id == show.id)
        )
    ).scalars().all()
    present = {a.kind for a in arts}
    missing = [k for k in reference.required_show_kinds() if k not in present]
    if missing:
        problems.append(
            {
                "code": "SHOW_PUBLISHED_REQUIRES_ARTWORK",
                "field": "artwork",
                "message": f"A published show must have poster and banner artwork. Missing: {', '.join(missing)}.",
                "hint": f"Upload via POST /shows/{show.id}/artwork.",
                "resource": {"type": "show", "id": show.id, "title": show.title},
            }
        )
    if problems:
        raise ApiError(
            422,
            "validation_error",
            f'"{show.title}" cannot be published yet. {len(problems)} problem(s) must be fixed first.',
            problems,
        )


@router.get("/shows")
async def list_shows(
    status: str | None = None,
    section: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    limit, offset = paginate_params(limit, offset)
    stmt = select(Show)
    if status:
        stmt = stmt.where(Show.status == status)
    if section:
        stmt = stmt.where(Show.section == section)
    if category:
        stmt = stmt.where(Show.category == category)
    if q:
        stmt = stmt.where(Show.title.ilike(f"%{q}%"))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Show.id).limit(limit).offset(offset)
    shows = (await session.execute(stmt)).scalars().all()
    artworks = (await session.execute(select(Artwork).where(Artwork.owner_type == "show"))).scalars().all()
    items = []
    for s in shows:
        sc, ec, tc = await _counts_for_show(session, s.id)
        items.append(show_dict(s, artworks, sc, ec, tc))
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/shows", status_code=201)
async def create_show(
    payload: ShowCreate,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    _validate_enums(category=payload.category, section=payload.section, status=payload.status)
    slug = payload.slug or slugify(payload.title)
    existing = (await session.execute(select(Show).where(Show.slug == slug))).scalar_one_or_none()
    if existing:
        raise ApiError(
            409,
            "conflict",
            f'A show with the slug "{slug}" already exists. Pick a different title or slug.',
            [
                {
                    "code": "SHOW_SLUG_UNIQUE",
                    "field": "slug",
                    "message": f'Slug "{slug}" is taken by show #{existing.id}.',
                    "hint": None,
                    "resource": {"type": "show", "id": existing.id},
                }
            ],
        )
    show = Show(
        slug=slug,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        section=payload.section,
        status=payload.status or "draft",
    )
    session.add(show)
    await session.flush()
    if show.status == "published":
        await _check_publish_requirements(session, show)
    await session.commit()
    return show_dict(show, [], 0, 0, 0)


@router.get("/shows/{show_id}")
async def get_show(
    show_id: int,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    show = (await session.execute(select(Show).where(Show.id == show_id))).scalar_one_or_none()
    if not show:
        raise ApiError(404, "not_found", f"Show #{show_id} was not found.")
    artworks = (
        await session.execute(
            select(Artwork).where(Artwork.owner_type == "show", Artwork.owner_id == show_id)
        )
    ).scalars().all()
    sc, ec, tc = await _counts_for_show(session, show_id)
    seasons = (
        await session.execute(select(Season).where(Season.show_id == show_id).order_by(Season.season_number))
    ).scalars().all()
    seasons_out = []
    for s in seasons:
        cnt = (
            await session.execute(select(func.count()).select_from(Episode).where(Episode.season_id == s.id))
        ).scalar_one()
        seasons_out.append({"id": s.id, "season_number": s.season_number, "title": s.title, "episode_count": cnt})
    out = show_dict(show, artworks, sc, ec, tc)
    out["seasons"] = seasons_out
    return out


@router.patch("/shows/{show_id}")
async def update_show(
    show_id: int,
    payload: ShowUpdate,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    show = (await session.execute(select(Show).where(Show.id == show_id))).scalar_one_or_none()
    if not show:
        raise ApiError(404, "not_found", f"Show #{show_id} was not found.")
    data = payload.model_dump(exclude_unset=True)
    _validate_enums(category=data.get("category"), section=data.get("section"), status=data.get("status"))
    if "slug" in data and data["slug"] != show.slug:
        existing = (await session.execute(select(Show).where(Show.slug == data["slug"]))).scalar_one_or_none()
        if existing:
            raise ApiError(
                409,
                "conflict",
                f'A show with the slug "{data["slug"]}" already exists. Pick a different title or slug.',
                [
                    {
                        "code": "SHOW_SLUG_UNIQUE",
                        "field": "slug",
                        "message": f'Slug "{data["slug"]}" is taken by show #{existing.id}.',
                        "hint": None,
                        "resource": {"type": "show", "id": existing.id},
                    }
                ],
            )
    for field, value in data.items():
        setattr(show, field, value)
    await session.flush()
    if show.status == "published":
        await _check_publish_requirements(session, show)
    await session.commit()
    artworks = (
        await session.execute(
            select(Artwork).where(Artwork.owner_type == "show", Artwork.owner_id == show_id)
        )
    ).scalars().all()
    sc, ec, tc = await _counts_for_show(session, show_id)
    return show_dict(show, artworks, sc, ec, tc)


@router.delete("/shows/{show_id}", status_code=204)
async def delete_show(
    show_id: int,
    user: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    show = (await session.execute(select(Show).where(Show.id == show_id))).scalar_one_or_none()
    if not show:
        raise ApiError(404, "not_found", f"Show #{show_id} was not found.")
    last_run = await get_last_successful_run(session)
    if last_run:
        # Best-effort live-catalogue check: if the show is currently published and a
        # catalogue has been generated, block deletion to avoid dangling references.
        if show.status == "published":
            raise ApiError(
                409,
                "conflict",
                f'"{show.title}" is live in catalogue version {last_run.version}. '
                "Archive it and re-publish before deleting.",
            )
    await session.delete(show)
    await session.commit()
