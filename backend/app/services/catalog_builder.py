"""Builds the published catalogue.json structure from the live DB state."""
import datetime as dt
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app import reference
from app.services.validation import load_all


def _artwork_map(artworks, owner_type, owner_id):
    return {
        a.kind: {"url": a.url, "width": a.width, "height": a.height}
        for a in artworks
        if a.owner_type == owner_type and a.owner_id == owner_id
    }


def _pick_default(rows, default_lang):
    for r in rows:
        if r.language == default_lang:
            return r
    return min(rows, key=lambda r: r.id)


async def build_catalog(session: AsyncSession):
    """Returns (catalog_dict_without_meta, counts, warnings, skipped_show_ids, skipped_episode_ids)."""
    shows, seasons, episodes, artworks = await load_all(session)
    default_lang = reference.default_language()
    nav_sections = reference.nav_sections()
    nav_keys = {s["key"] for s in nav_sections}

    seasons_by_show = defaultdict(list)
    for s in seasons:
        seasons_by_show[s.show_id].append(s)

    warnings = []
    skipped_shows = []
    skipped_episodes = []

    # Determine blocking content_group duplicates first (handled by caller: publish blocks entirely).
    published_shows = [s for s in shows if s.status == "published"]

    sections_out = {key: [] for key in nav_keys}
    counts_languages: dict[str, int] = defaultdict(int)
    total_entries = 0
    total_rows_considered = 0
    total_collapsed = 0
    total_trailers = 0

    for show in published_shows:
        show_artwork = _artwork_map(artworks, "show", show.id)
        if not show.section or show.section not in nav_keys:
            skipped_shows.append(show.id)
            warnings.append(
                {
                    "code": "SHOW_SKIPPED",
                    "message": f'"{show.title}" was skipped: a published show must belong to a section.',
                    "resource": {"type": "show", "id": show.id},
                }
            )
            continue
        missing_show_art = [k for k in reference.required_show_kinds() if k not in show_artwork]
        if missing_show_art:
            skipped_shows.append(show.id)
            warnings.append(
                {
                    "code": "SHOW_SKIPPED",
                    "message": f'"{show.title}" was skipped: missing {", ".join(missing_show_art)} artwork.',
                    "resource": {"type": "show", "id": show.id},
                }
            )
            continue

        show_seasons = sorted(seasons_by_show.get(show.id, []), key=lambda s: s.season_number)

        # group episodes per season by content_group
        cg_groups_by_season: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for ep in episodes:
            if ep.show_id != show.id or ep.status != "published":
                continue
            season = next((s for s in show_seasons if s.id == ep.season_id), None)
            if not season:
                continue
            total_rows_considered += 1
            is_trailer = season.season_number == 0
            if is_trailer and ep.episode_number is not None:
                skipped_episodes.append(ep.id)
                warnings.append(
                    {
                        "code": "EPISODE_SKIPPED",
                        "message": f'"{ep.title}" was skipped: trailers must not carry an episode number.',
                        "resource": {"type": "episode", "id": ep.id},
                    }
                )
                continue
            if not is_trailer and (ep.duration_seconds is None or ep.duration_seconds <= 0):
                skipped_episodes.append(ep.id)
                warnings.append(
                    {
                        "code": "EPISODE_SKIPPED",
                        "message": f'"{ep.title}" was skipped: published episode has no duration.',
                        "resource": {"type": "episode", "id": ep.id},
                    }
                )
                continue
            ep_art = _artwork_map(artworks, "episode", ep.id)
            missing = [k for k in reference.required_episode_kinds() if k not in ep_art]
            if missing:
                skipped_episodes.append(ep.id)
                warnings.append(
                    {
                        "code": "EPISODE_SKIPPED",
                        "message": f'"{ep.title}" was skipped: missing {", ".join(missing)} artwork.',
                        "resource": {"type": "episode", "id": ep.id},
                    }
                )
                continue
            cg_groups_by_season[season.id][ep.content_group].append(ep)

        seasons_out = []
        trailers_out = []
        show_languages = set()

        for season in show_seasons:
            groups = cg_groups_by_season.get(season.id, {})
            entries = []
            for cg, rows in groups.items():
                langs = sorted({r.language for r in rows}, key=lambda l: (l != default_lang, l))
                default_row = _pick_default(rows, default_lang)
                ep_art = _artwork_map(artworks, "episode", default_row.id)
                show_languages.update(langs)
                total_collapsed += len(rows) - 1
                for l in langs:
                    counts_languages[l] += 1
                entry = {
                    "content_group": cg,
                    "episode_number": default_row.episode_number,
                    "title": default_row.title,
                    "synopsis": default_row.synopsis,
                    "duration_seconds": default_row.duration_seconds,
                    "languages": langs,
                    "titles_by_language": {r.language: r.title for r in rows},
                    "artwork": ep_art,
                }
                entries.append(entry)
                total_entries += 1

            if season.season_number == 0:
                trailers_out = sorted(entries, key=lambda e: (e["content_group"]))
                total_trailers += len(trailers_out)
            else:
                entries.sort(key=lambda e: (e["episode_number"] is None, e["episode_number"]))
                seasons_out.append(
                    {
                        "season_number": season.season_number,
                        "title": season.title or f"Season {season.season_number}",
                        "episode_count": len(entries),
                        "episodes": entries,
                    }
                )

        show_out = {
            "id": show.id,
            "slug": show.slug,
            "title": show.title,
            "description": show.description,
            "category": show.category,
            "category_label": reference.category_label(show.category),
            "languages": sorted(show_languages, key=lambda l: (l != default_lang, l)),
            "artwork": show_artwork,
            "seasons": seasons_out,
            "trailers": trailers_out,
        }
        sections_out[show.section].append(show_out)

    sections_final = []
    for sec in nav_sections:
        shows_list = sections_out.get(sec["key"], [])
        if not shows_list:
            continue
        sections_final.append(
            {
                "key": sec["key"],
                "label": sec["label"],
                "sort_order": sec["sort_order"],
                "shows": shows_list,
            }
        )

    catalog = {
        "reference_version": reference.load_reference()["reference_version"],
        "languages": sorted({l for l in counts_languages.keys()} | {default_lang}, key=lambda l: (l != default_lang, l)),
        "sections": sections_final,
    }

    counts = {
        "sections": len(sections_final),
        "shows": sum(len(s["shows"]) for s in sections_final),
        "catalog_entries": total_entries,
        "episode_rows_considered": total_rows_considered,
        "rows_collapsed": total_collapsed,
        "trailers": total_trailers,
        "languages": dict(counts_languages),
        "skipped_shows": len(skipped_shows),
        "skipped_episodes": len(skipped_episodes),
    }
    return catalog, counts, warnings, skipped_shows, skipped_episodes
