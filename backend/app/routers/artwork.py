import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import reference
from app.database import get_session
from app.deps import CurrentUser, require_editor
from app.errors import ApiError
from app.models import Artwork, Episode, Show
from app.serializers import artwork_dict
from app.services.artwork import EXT_BY_MIME, validate_and_probe
from app.storage import get_storage

router = APIRouter(tags=["artwork"])


def _artwork_out(a: Artwork) -> dict:
    d = artwork_dict(a)
    d["aspect_ratio"] = None
    spec = reference.artwork_spec(a.kind)
    if spec:
        d["aspect_ratio"] = spec["aspect_ratio"]
    d["alt_text"] = a.alt_text
    d["created_at"] = a.created_at.isoformat()
    if a.owner_type == "episode":
        d["episode_id"] = a.owner_id
    else:
        d["show_id"] = a.owner_id
    return d


async def _upload(
    session: AsyncSession,
    owner_type: str,
    owner_id: int,
    owner_title: str,
    kind: str,
    file: UploadFile,
    alt_text: str | None,
    allowed_kinds: list[str],
):
    if kind not in allowed_kinds:
        raise ApiError(
            422,
            "validation_error",
            f'"{kind}" is not a valid artwork kind for this resource.',
            [
                {
                    "code": "ENUM_NOT_ALLOWED",
                    "field": "kind",
                    "message": f"Allowed kinds: {', '.join(allowed_kinds)}.",
                    "hint": None,
                    "resource": None,
                }
            ],
        )
    data = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    width, height = validate_and_probe(kind, mime_type, data)

    ext = EXT_BY_MIME.get(mime_type, "bin")
    key = f"{owner_type}/{owner_id}/{kind}-{uuid.uuid4().hex[:8]}.{ext}"
    storage = get_storage()
    url = storage.write_bytes(key, data, mime_type)

    existing = (
        await session.execute(
            select(Artwork).where(Artwork.owner_type == owner_type, Artwork.owner_id == owner_id, Artwork.kind == kind)
        )
    ).scalar_one_or_none()
    if existing:
        old_key = existing.storage_key
        existing.url = url
        existing.storage_key = key
        existing.width = width
        existing.height = height
        existing.file_size_bytes = len(data)
        existing.mime_type = mime_type
        existing.alt_text = alt_text
        art = existing
        try:
            storage.delete(old_key)
        except Exception:
            pass
    else:
        art = Artwork(
            owner_type=owner_type,
            owner_id=owner_id,
            kind=kind,
            url=url,
            storage_key=key,
            width=width,
            height=height,
            file_size_bytes=len(data),
            mime_type=mime_type,
            alt_text=alt_text,
        )
        session.add(art)
    await session.commit()
    return art


@router.post("/episodes/{episode_id}/artwork", status_code=201)
async def upload_episode_artwork(
    episode_id: int,
    kind: str = Form(...),
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    ep = (await session.execute(select(Episode).where(Episode.id == episode_id))).scalar_one_or_none()
    if not ep:
        raise ApiError(404, "not_found", f"Episode #{episode_id} was not found.")
    art = await _upload(
        session, "episode", episode_id, ep.title, kind, file, alt_text, reference.required_episode_kinds()
    )
    return _artwork_out(art)


@router.get("/episodes/{episode_id}/artwork")
async def list_episode_artwork(
    episode_id: int,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    ep = (await session.execute(select(Episode).where(Episode.id == episode_id))).scalar_one_or_none()
    if not ep:
        raise ApiError(404, "not_found", f"Episode #{episode_id} was not found.")
    arts = (
        await session.execute(
            select(Artwork).where(Artwork.owner_type == "episode", Artwork.owner_id == episode_id)
        )
    ).scalars().all()
    present = {a.kind for a in arts}
    missing = [k for k in reference.required_episode_kinds() if k not in present]
    return {"items": [_artwork_out(a) for a in arts], "missing_kinds": missing}


@router.post("/shows/{show_id}/artwork", status_code=201)
async def upload_show_artwork(
    show_id: int,
    kind: str = Form(...),
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    show = (await session.execute(select(Show).where(Show.id == show_id))).scalar_one_or_none()
    if not show:
        raise ApiError(404, "not_found", f"Show #{show_id} was not found.")
    art = await _upload(session, "show", show_id, show.title, kind, file, alt_text, reference.required_show_kinds())
    return _artwork_out(art)


@router.get("/shows/{show_id}/artwork")
async def list_show_artwork(
    show_id: int,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    show = (await session.execute(select(Show).where(Show.id == show_id))).scalar_one_or_none()
    if not show:
        raise ApiError(404, "not_found", f"Show #{show_id} was not found.")
    arts = (
        await session.execute(
            select(Artwork).where(Artwork.owner_type == "show", Artwork.owner_id == show_id)
        )
    ).scalars().all()
    present = {a.kind for a in arts}
    missing = [k for k in reference.required_show_kinds() if k not in present]
    return {"items": [_artwork_out(a) for a in arts], "missing_kinds": missing}


@router.delete("/artwork/{artwork_id}", status_code=204)
async def delete_artwork(
    artwork_id: int,
    user: CurrentUser = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    art = (await session.execute(select(Artwork).where(Artwork.id == artwork_id))).scalar_one_or_none()
    if not art:
        raise ApiError(404, "not_found", f"Artwork #{artwork_id} was not found.")

    if art.owner_type == "episode":
        ep = (await session.execute(select(Episode).where(Episode.id == art.owner_id))).scalar_one_or_none()
        if ep and ep.status == "published":
            required = reference.required_episode_kinds()
            if art.kind in required:
                raise ApiError(
                    409,
                    "conflict",
                    f'"{ep.title}" is published and needs a {art.kind}. '
                    "Unpublish the episode or upload a replacement first.",
                )
    else:
        show = (await session.execute(select(Show).where(Show.id == art.owner_id))).scalar_one_or_none()
        if show and show.status == "published":
            required = reference.required_show_kinds()
            if art.kind in required:
                raise ApiError(
                    409,
                    "conflict",
                    f'"{show.title}" is published and needs a {art.kind}. '
                    "Unpublish the show or upload a replacement first.",
                )

    storage = get_storage()
    try:
        storage.delete(art.storage_key)
    except Exception:
        pass
    await session.delete(art)
    await session.commit()
