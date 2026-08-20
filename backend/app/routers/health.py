import datetime as dt

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import PublishRun

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(response: Response, session: AsyncSession = Depends(get_session)):
    catalog_version = None
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
        result = await session.execute(
            select(PublishRun.version)
            .where(PublishRun.status.in_(["success", "success_with_warnings"]))
            .order_by(PublishRun.version.desc())
        )
        catalog_version = result.scalars().first()
    except Exception:
        db_ok = False

    body = {
        "status": "ok" if db_ok else "degraded",
        "version": settings.app_version,
        "database": "ok" if db_ok else "unreachable",
        "catalog_version": catalog_version,
        "time": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if not db_ok:
        response.status_code = 503
    return body
