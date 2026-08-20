"""Shared validation rules used by CRUD endpoints, publish, and the validation report.

Mirrors section 0.3 of docs/API_CONTRACT.md.
"""
import datetime as dt
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import reference
from app.models import Artwork, Episode, Season, Show


def detail(code, field, message, hint=None, resource=None, related=None):
    d = {"code": code, "field": field, "message": message, "hint": hint, "resource": resource}
    if related is not None:
        d["related"] = related
    return d


def episode_resource(ep: Episode, title=None):
    return {
        "type": "episode",
        "id": ep.id,
        "title": title if title is not None else ep.title,
        "season_number": None,
        "episode_number": ep.episode_number,
        "language": ep.language,
        "content_group": ep.content_group,
    }


def show_resource(show: Show):
    return {"type": "show", "id": show.id, "title": show.title}


async def load_all(session: AsyncSession):
    shows = (await session.execute(select(Show))).scalars().all()
    seasons = (await session.execute(select(Season))).scalars().all()
    episodes = (await session.execute(select(Episode))).scalars().all()
    artworks = (await session.execute(select(Artwork))).scalars().all()
    return shows, seasons, episodes, artworks


def artwork_issues(art: Artwork) -> list[dict]:
    issues = []
    spec = reference.artwork_spec(art.kind)
    if spec:
        ratio = art.width / art.height if art.height else 0
        tol = reference.artwork_tolerance()
        expected = spec["aspect_ratio_value"]
        if abs(ratio - expected) / expected > tol:
            issues.append(
                (
                    "ARTWORK_ASPECT_RATIO",
                    detail(
                        "ARTWORK_ASPECT_RATIO",
                        "file",
                        f"{art.kind.capitalize()}s must be {spec['aspect_ratio']} (about "
                        f"{spec['width']}x{spec['height']}). The uploaded image is "
                        f"{art.width}x{art.height}.",
                        "Crop or re-export at the correct dimensions and upload again.",
                    ),
                )
            )
    max_bytes = reference.artwork_max_bytes()
    if art.file_size_bytes > max_bytes:
        issues.append(
            (
                "ARTWORK_SIZE_LIMIT",
                detail(
                    "ARTWORK_SIZE_LIMIT",
                    "file",
                    f"The file is {art.file_size_bytes // 1024} KB. Artwork must be "
                    f"{max_bytes // 1024} KB or smaller.",
                    "Re-export the image as JPEG at ~80% quality, or use WebP.",
                ),
            )
        )
    return issues


async def run_validation_report(session: AsyncSession, show_id: int | None = None, severity: str | None = None):
    shows, seasons, episodes, artworks = await load_all(session)
    shows_by_id = {s.id: s for s in shows}
    season_by_id = {s.id: s for s in seasons}

    artwork_by_owner: dict[tuple[str, int], dict[str, Artwork]] = defaultdict(dict)
    for a in artworks:
        artwork_by_owner[(a.owner_type, a.owner_id)][a.kind] = a

    issues_by_show: dict[int, list[dict]] = defaultdict(list)

    # Show-level rules
    for show in shows:
        if show.status == "published" and not show.section:
            issues_by_show[show.id].append(
                {
                    "code": "SHOW_PUBLISHED_REQUIRES_SECTION",
                    "severity": "blocking",
                    "message": f'"{show.title}" is published but has no section.',
                    "hint": f"PATCH /shows/{show.id} with a valid section.",
                    "resource": show_resource(show),
                    "field": "section",
                }
            )
        if show.status == "published":
            owned = artwork_by_owner.get(("show", show.id), {})
            missing = [k for k in reference.required_show_kinds() if k not in owned]
            if missing:
                issues_by_show[show.id].append(
                    {
                        "code": "SHOW_PUBLISHED_REQUIRES_ARTWORK",
                        "severity": "blocking",
                        "message": f'"{show.title}" is published but is missing {", ".join(missing)} artwork.',
                        "hint": f"Upload the missing artwork via POST /shows/{show.id}/artwork.",
                        "resource": show_resource(show),
                        "field": "artwork",
                    }
                )

    # Episode-level rules
    content_group_lang: dict[tuple[str, str], list[Episode]] = defaultdict(list)
    for ep in episodes:
        season = season_by_id.get(ep.season_id)
        is_trailer = season is not None and season.season_number == 0
        show = shows_by_id.get(ep.show_id)

        if is_trailer and ep.episode_number is not None:
            issues_by_show[ep.show_id].append(
                {
                    "code": "TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER",
                    "severity": "blocking",
                    "message": f'"{ep.title}" is a season-0 trailer but has episode_number {ep.episode_number}.',
                    "hint": "Send episode_number: null, or move the episode to season 1 or later.",
                    "resource": episode_resource(ep),
                    "field": "episode_number",
                }
            )

        if ep.status == "published":
            if not is_trailer and (ep.duration_seconds is None or ep.duration_seconds <= 0):
                issues_by_show[ep.show_id].append(
                    {
                        "code": "EPISODE_PUBLISHED_REQUIRES_DURATION",
                        "severity": "blocking",
                        "message": f'"{ep.title}" is published but has no duration.',
                        "hint": f"Set duration_seconds on episode #{ep.id}, or move it back to draft.",
                        "resource": episode_resource(ep),
                        "field": "duration_seconds",
                    }
                )
            owned = artwork_by_owner.get(("episode", ep.id), {})
            missing = [k for k in reference.required_episode_kinds() if k not in owned]
            if missing:
                issues_by_show[ep.show_id].append(
                    {
                        "code": "EPISODE_PUBLISHED_REQUIRES_ARTWORK",
                        "severity": "blocking",
                        "message": f'"{ep.title}" is published but is missing {", ".join(missing)} artwork.',
                        "hint": f"Upload missing artwork via POST /episodes/{ep.id}/artwork.",
                        "resource": episode_resource(ep),
                        "field": "artwork",
                    }
                )

        content_group_lang[(ep.content_group, ep.language)].append(ep)

    for (cg, lang), rows in content_group_lang.items():
        if len(rows) > 1:
            rows_sorted = sorted(rows, key=lambda r: r.id)
            newest = rows_sorted[-1]
            others = rows_sorted[:-1]
            issues_by_show[newest.show_id].append(
                {
                    "code": "CONTENT_GROUP_LANGUAGE_UNIQUE",
                    "severity": "blocking",
                    "message": f'Content group "{cg}" has two {reference.language_label(lang)} rows, '
                    "so it cannot be collapsed into a single catalogue entry.",
                    "hint": f"Delete or re-language episode #{newest.id}, or give it its own content_group.",
                    "resource": episode_resource(newest),
                    "related": [{"type": "episode", "id": o.id, "title": o.title} for o in others],
                    "field": "content_group",
                }
            )

    # Artwork-level rules (attributed to owning show)
    for a in artworks:
        for code, d in artwork_issues(a):
            if a.owner_type == "show":
                show_id_for = a.owner_id
                resource = {"type": "show", "id": shows_by_id[a.owner_id].id, "title": shows_by_id[a.owner_id].title} if a.owner_id in shows_by_id else {"type": "show", "id": a.owner_id}
            else:
                ep = next((e for e in episodes if e.id == a.owner_id), None)
                if not ep:
                    continue
                show_id_for = ep.show_id
                resource = episode_resource(ep)
            d = dict(d)
            d["resource"] = resource
            issues_by_show[show_id_for].append(
                {
                    "code": code,
                    "severity": "blocking",
                    "message": d["message"],
                    "hint": d["hint"],
                    "resource": resource,
                    "field": "file",
                }
            )

    by_show = []
    by_type: dict[str, int] = defaultdict(int)
    total_blocking = 0
    total_warning = 0
    for show in shows:
        if show_id is not None and show.id != show_id:
            continue
        issues = issues_by_show.get(show.id, [])
        if severity:
            issues = [i for i in issues if i["severity"] == severity]
        if not issues:
            continue
        blocking = [i for i in issues if i["severity"] == "blocking"]
        warning = [i for i in issues if i["severity"] == "warning"]
        for i in issues:
            by_type[i["code"]] += 1
        total_blocking += len(blocking)
        total_warning += len(warning)
        by_show.append(
            {
                "show": {
                    "id": show.id,
                    "slug": show.slug,
                    "title": show.title,
                    "status": show.status,
                    "section": show.section,
                },
                "blocking_count": len(blocking),
                "warning_count": len(warning),
                "issues": issues,
            }
        )

    shows_affected = len(by_show)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "publishable": total_blocking == 0,
        "summary": {
            "blocking_issues": total_blocking,
            "warnings": total_warning,
            "shows_affected": shows_affected,
            "shows_total": len(shows),
            "by_type": dict(by_type),
        },
        "by_show": by_show,
    }
