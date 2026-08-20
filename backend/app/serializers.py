from app import reference
from app.models import Artwork, Episode, Season, Show


def artwork_dict(a: Artwork) -> dict:
    return {
        "id": a.id,
        "kind": a.kind,
        "url": a.url,
        "width": a.width,
        "height": a.height,
        "file_size_bytes": a.file_size_bytes,
        "mime_type": a.mime_type,
    }


def show_dict(show: Show, artworks: list[Artwork], season_count: int, episode_count: int, trailer_count: int) -> dict:
    return {
        "id": show.id,
        "slug": show.slug,
        "title": show.title,
        "description": show.description,
        "category": show.category,
        "section": show.section,
        "status": show.status,
        "artwork": [artwork_dict(a) for a in artworks if a.owner_type == "show" and a.owner_id == show.id],
        "season_count": season_count,
        "episode_count": episode_count,
        "trailer_count": trailer_count,
        "created_at": show.created_at.isoformat(),
        "updated_at": show.updated_at.isoformat(),
    }


def season_dict(season: Season, episode_count: int) -> dict:
    return {
        "id": season.id,
        "show_id": season.show_id,
        "season_number": season.season_number,
        "title": season.title,
        "is_trailer_season": season.season_number == 0,
        "episode_count": episode_count,
    }


def episode_dict(ep: Episode, season_number: int, artworks: list[Artwork]) -> dict:
    ep_artworks = [a for a in artworks if a.owner_type == "episode" and a.owner_id == ep.id]
    present_kinds = {a.kind for a in ep_artworks}
    missing = [k for k in reference.required_episode_kinds() if k not in present_kinds]
    return {
        "id": ep.id,
        "season_id": ep.season_id,
        "show_id": ep.show_id,
        "season_number": season_number,
        "episode_number": ep.episode_number,
        "title": ep.title,
        "synopsis": ep.synopsis,
        "content_group": ep.content_group,
        "language": ep.language,
        "duration_seconds": ep.duration_seconds,
        "status": ep.status,
        "is_trailer": season_number == 0,
        "artwork": [artwork_dict(a) for a in ep_artworks],
        "missing_artwork_kinds": missing,
        "created_at": ep.created_at.isoformat(),
        "updated_at": ep.updated_at.isoformat(),
    }
