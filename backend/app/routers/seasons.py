from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.deps import CurrentUser, require_admin, require_editor
from app.errors import ApiError
from app.models import Episode, Season, Show
from app.schemas import SeasonCreate, SeasonUpdate
from app.serializers import season_dict
from app.utils import paginate_params

router = APIRouter(tags=["seasons"])


@router.get("/shows/{show_id}/seasons")
async def list_seasons(
    show_id: int,
    include_trailers: bool = True,
    limit: int = 50,
    offset: int = 0,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    show = (await session.execute(select(Show).where(Show.id == show_id))).scalar_one_or_none()
    if not show:
        raise ApiError(404, "not_found", f"Show #{show_id} was not found.")
    limit, offset = paginate_params(limit, offset)
    stmt = select(Season).where(Season.show_id == show_id)
    if not include_trailers:
        stmt = stmt.where(Season.season_number != 0)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Season.season_number).limit(limit).offset(offset)
    seasons = (await session.execute(stmt)).scalars().all()
    items = []
    for s in seasons:
        cnt = (await session.execute(select(func.count()).select_from(Episode).where(Episode.season_id == s.id))).scalar_one()
        items.append(season_dict(s, cnt))
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/shows/{show_id}/seasons", status_code=201)
async def create_season(show_id: int, payload: SeasonCreate, user: CurrentUser = Depends(require_editor), session: AsyncSession = Depends(get_session)):
    show = (await session.execute(select(Show).where(Show.id == show_id))).scalar_one_or_none()
    if not show:
        raise ApiError(404, "not_found", f"Show #{show_id} was not found.")
    existing = (
        await session.execute(select(Season).where(Season.show_id == show_id, Season.season_number == payload.season_number))
    ).scalar_one_or_none()
    if existing:
        raise ApiError(
            409,
            "conflict",
            f'Season {payload.season_number} already exists for "{show.title}".',
            [{"code": "SEASON_NUMBER_UNIQUE", "field": "season_number", "message": f"Season {payload.season_number} already exists.", "hint": None, "resource": {"type": "season", "id": existing.id}}],
        )
    season = Season(show_id=show_id, season_number=payload.season_number, title=payload.title)
    session.add(season)
    await session.commit()
    return season_dict(season, 0)


@router.patch("/seasons/{season_id}")
async def update_season(season_id: int, payload: SeasonUpdate, user: CurrentUser = Depends(require_editor), session: AsyncSession = Depends(get_session)):
    season = (await session.execute(select(Season).where(Season.id == season_id))).scalar_one_or_none()
    if not season:
        raise ApiError(404, "not_found", f"Season #{season_id} was not found.")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(season, field, value)
    await session.commit()
    cnt = (await session.execute(select(func.count()).select_from(Episode).where(Episode.season_id == season.id))).scalar_one()
    return season_dict(season, cnt)


@router.delete("/seasons/{season_id}", status_code=204)
async def delete_season(season_id: int, user: CurrentUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    season = (await session.execute(select(Season).where(Season.id == season_id))).scalar_one_or_none()
    if not season:
        raise ApiError(404, "not_found", f"Season #{season_id} was not found.")
    published = (
        await session.execute(select(func.count()).select_from(Episode).where(Episode.season_id == season_id, Episode.status == "published"))
    ).scalar_one()
    if published:
        raise ApiError(409, "conflict", f"Season {season.season_number} still holds {published} published episode(s). Unpublish them before deleting.")
    await session.delete(season)
    await session.commit()
    return None
