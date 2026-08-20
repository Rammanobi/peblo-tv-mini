import datetime as dt
import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ApiError
from app.models import PublishRun
from app.services.catalog_builder import build_catalog
from app.services.validation import run_validation_report
from app.storage import get_storage

CATALOG_POINTER_KEY = "catalog/pointer.json"


def _catalog_key(version: int) -> str:
    return f"catalog/catalogue.v{version}.json"


def _stable_hash(catalog: dict) -> str:
    payload = json.dumps(catalog, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


async def get_last_successful_run(session: AsyncSession) -> PublishRun | None:
    result = await session.execute(
        select(PublishRun)
        .where(PublishRun.status.in_(["success", "success_with_warnings"]))
        .order_by(PublishRun.version.desc())
    )
    return result.scalars().first()


async def run_publish(session: AsyncSession, user_id: int, user_email: str, dry_run: bool, note: str | None):
    started = dt.datetime.now(dt.timezone.utc)

    report = await run_validation_report(session)
    cg_issues = []
    for show_entry in report["by_show"]:
        for issue in show_entry["issues"]:
            if issue["code"] == "CONTENT_GROUP_LANGUAGE_UNIQUE":
                cg_issues.append(issue | {"show": show_entry["show"]})

    if cg_issues:
        n_shows = len({i["show"]["id"] for i in cg_issues})
        details = []
        for i in cg_issues:
            d = dict(i)
            d.pop("show", None)
            d.pop("severity", None)
            details.append(d)
        raise ApiError(
            422,
            "validation_error",
            f"Publish blocked. {len(cg_issues)} issue(s) across {n_shows} show(s) must be fixed first.",
            details,
        )

    catalog, counts, warnings, _skipped_shows, _skipped_episodes = await build_catalog(session)
    last_run = await get_last_successful_run(session)
    new_hash = _stable_hash(catalog)

    # A hash match against the DB record is not sufficient on its own — the
    # object storage backing the last run could have been wiped or swapped
    # (e.g. a fresh volume, a storage migration) without the DB knowing.
    # Only skip the write if the recorded version's file is verifiably still
    # present; otherwise treat it as if nothing had ever been published and
    # write fresh, so a reader can never be pointed at a version that isn't
    # actually there.
    is_noop = False
    if last_run is not None and last_run.catalog_hash == new_hash:
        storage = get_storage()
        is_noop = (
            storage.read_bytes(_catalog_key(last_run.version)) is not None
            and storage.read_bytes(CATALOG_POINTER_KEY) is not None
        )

    status = "success_with_warnings" if warnings else "success"
    run_id = "pub_" + uuid.uuid4().hex[:16].upper()
    duration_ms = int((dt.datetime.now(dt.timezone.utc) - started).total_seconds() * 1000)

    if dry_run:
        return {
            "run_id": run_id,
            "status": status,
            "version": None,
            "dry_run": True,
            "published_at": started.isoformat().replace("+00:00", "Z"),
            "published_by": {"id": user_id, "email": user_email},
            "duration_ms": duration_ms,
            "note": note,
            "counts": counts,
            "warnings": warnings,
            "catalog_url": "/api/v1/catalog",
        }

    storage = get_storage()
    if is_noop:
        version = last_run.version
    else:
        version = (last_run.version if last_run else 0) + 1
        catalog_with_meta = dict(catalog)
        catalog_with_meta["catalog_version"] = version
        catalog_with_meta["generated_at"] = started.isoformat().replace("+00:00", "Z")
        body = json.dumps(catalog_with_meta, indent=2, ensure_ascii=False).encode("utf-8")
        storage.write_bytes(_catalog_key(version), body, "application/json")
        pointer = json.dumps({"version": version, "key": _catalog_key(version)}).encode("utf-8")
        storage.write_bytes(CATALOG_POINTER_KEY, pointer, "application/json")

    run = PublishRun(
        run_id=run_id,
        status=status,
        version=version,
        published_by_id=user_id,
        note=note,
        dry_run=False,
        duration_ms=duration_ms,
        counts_json=json.dumps(counts),
        warnings_json=json.dumps(warnings),
        catalog_hash=new_hash,
        published_at=started,
    )
    session.add(run)
    await session.commit()

    return {
        "run_id": run_id,
        "status": status,
        "version": version,
        "dry_run": False,
        "published_at": started.isoformat().replace("+00:00", "Z"),
        "published_by": {"id": user_id, "email": user_email},
        "duration_ms": duration_ms,
        "note": note,
        "counts": counts,
        "warnings": warnings,
        "catalog_url": "/api/v1/catalog",
    }


async def get_current_catalog() -> dict | None:
    storage = get_storage()
    pointer_bytes = storage.read_bytes(CATALOG_POINTER_KEY)
    if not pointer_bytes:
        return None
    pointer = json.loads(pointer_bytes)
    catalog_bytes = storage.read_bytes(pointer["key"])
    if not catalog_bytes:
        return None
    return json.loads(catalog_bytes)
