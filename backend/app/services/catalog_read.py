from app.errors import ApiError
from app.services.publish import get_current_catalog


async def load_catalog_or_404() -> dict:
    catalog = await get_current_catalog()
    if not catalog:
        raise ApiError(
            404,
            "not_found",
            "No catalogue has been published yet. An admin must run a publish first.",
        )
    return catalog


def search_catalog(catalog: dict, q, category, language, section, limit, offset):
    results = []
    for sec in catalog.get("sections", []):
        if section and sec["key"] != section:
            continue
        for show in sec["shows"]:
            if category and show["category"] != category:
                continue
            show_matched = []
            if q and q.lower() in show["title"].lower():
                show_matched.append("title")
            if q and show.get("description") and q.lower() in show["description"].lower():
                show_matched.append("description")
            if (not q or show_matched) and (not language or language in show["languages"]):
                if not q or show_matched:
                    results.append(
                        {
                            "type": "show",
                            "content_group": None,
                            "title": show["title"],
                            "synopsis": show.get("description"),
                            "duration_seconds": None,
                            "languages": show["languages"],
                            "season_number": None,
                            "episode_number": None,
                            "show": {
                                "id": show["id"],
                                "slug": show["slug"],
                                "title": show["title"],
                                "section": sec["key"],
                                "category": show["category"],
                            },
                            "artwork": show.get("artwork", {}),
                            "matched_on": show_matched,
                        }
                    )

            for season in show["seasons"]:
                for ep in season["episodes"]:
                    matched = []
                    if q:
                        ql = q.lower()
                        if ql in ep["title"].lower():
                            matched.append("title")
                        for t in ep.get("titles_by_language", {}).values():
                            if ql in t.lower() and "title" not in matched:
                                matched.append("title")
                        if ep.get("synopsis") and ql in ep["synopsis"].lower():
                            matched.append("synopsis")
                        if not matched:
                            continue
                    if language and language not in ep["languages"]:
                        continue
                    results.append(
                        {
                            "type": "episode",
                            "content_group": ep["content_group"],
                            "title": ep["title"],
                            "synopsis": ep.get("synopsis"),
                            "duration_seconds": ep.get("duration_seconds"),
                            "languages": ep["languages"],
                            "season_number": season["season_number"],
                            "episode_number": ep.get("episode_number"),
                            "show": {
                                "id": show["id"],
                                "slug": show["slug"],
                                "title": show["title"],
                                "section": sec["key"],
                                "category": show["category"],
                            },
                            "artwork": ep.get("artwork", {}),
                            "matched_on": matched,
                        }
                    )

    total = len(results)
    page = results[offset : offset + limit]
    return page, total
