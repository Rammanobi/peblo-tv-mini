import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.deps import CurrentUser, require_admin, require_editor
from app.models import PublishRun, User
from app.schemas import PublishRequest
from app.services.publish import run_publish
from app.services.validation import run_validation_report
from app.utils import paginate_params

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/catalog/publish")
async def publish(payload: PublishRequest = PublishRequest(), user: CurrentUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return await run_publish(session, user.id, user.email, payload.dry_run, payload.note)


@router.get("/catalog/publish-runs")
async def publish_runs(limit: int = 50, offset: int = 0, user: CurrentUser = Depends(require_editor), session: AsyncSession = Depends(get_session)):
    limit, offset = paginate_params(limit, offset)
    total = (await session.execute(select(PublishRun))).scalars().all()
    total_count = len(total)
    rows = sorted(total, key=lambda r: r.id, reverse=True)[offset : offset + limit]

    user_ids = {r.published_by_id for r in rows if r.published_by_id}
    users_by_id: dict[int, User] = {}
    if user_ids:
        result = await session.execute(select(User).where(User.id.in_(user_ids)))
        users_by_id = {u.id: u for u in result.scalars().all()}

    items = []
    for r in rows:
        warnings = json.loads(r.warnings_json or "[]")
        published_by = None
        if r.published_by_id:
            actor = users_by_id.get(r.published_by_id)
            published_by = {
                "id": r.published_by_id,
                "email": actor.email if actor else None,
                "name": actor.name if actor else None,
            }
        items.append(
            {
                "run_id": r.run_id,
                "status": r.status,
                "version": r.version,
                "published_at": r.published_at.isoformat() if r.published_at else None,
                "published_by": published_by,
                "counts": json.loads(r.counts_json or "{}"),
                "warning_count": len(warnings),
            }
        )
    return {"items": items, "total": total_count, "limit": limit, "offset": offset}


@router.get("/validation-report")
async def validation_report(
    show_id: int | None = None,
    severity: str | None = Query(default=None, pattern="^(blocking|warning)$"),
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    return await run_validation_report(session, show_id=show_id, severity=severity)
