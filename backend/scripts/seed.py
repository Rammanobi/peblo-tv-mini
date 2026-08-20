"""Idempotent seed loader.

Loads data/seed_shows.json (verbatim, including its 7 deliberate defects
documented in data/SEED_NOTES.md — nothing here "fixes" them) plus two
fixture users, into the database. Skips entirely if any show already exists.
"""
import asyncio
import json

from sqlalchemy import select

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Artwork, Episode, Season, Show, User
from app.security import hash_password


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_if_needed() -> None:
    async with SessionLocal() as session:
        existing = (await session.execute(select(Show).limit(1))).scalar_one_or_none()
        if existing:
            return

        admin = User(email="admin@peblo.tv", name="Ada Admin", password_hash=hash_password("admin123"), role="admin")
        editor = User(email="editor@peblo.tv", name="Ada Editor", password_hash=hash_password("hunter2"), role="editor")
        session.add_all([admin, editor])

        data = _load_json(settings.seed_path)
        for show_row in data["shows"]:
            show = Show(
                slug=show_row["slug"],
                title=show_row["title"],
                description=show_row.get("description"),
                category=show_row["category"],
                section=show_row.get("section"),
                status=show_row["status"],
            )
            session.add(show)
            await session.flush()

            for art in show_row.get("artwork", []):
                session.add(
                    Artwork(
                        owner_type="show",
                        owner_id=show.id,
                        kind=art["kind"],
                        url=art["url"],
                        storage_key=art.get("file_name", art["url"]),
                        width=art["width"],
                        height=art["height"],
                        file_size_bytes=art["file_size_bytes"],
                        mime_type=art["mime_type"],
                    )
                )

            for season_row in show_row.get("seasons", []):
                season = Season(
                    show_id=show.id,
                    season_number=season_row["season_number"],
                    title=season_row.get("title"),
                )
                session.add(season)
                await session.flush()

                for ep_row in season_row.get("episodes", []):
                    ep = Episode(
                        season_id=season.id,
                        show_id=show.id,
                        episode_number=ep_row.get("episode_number"),
                        title=ep_row["title"],
                        synopsis=ep_row.get("synopsis"),
                        content_group=ep_row["content_group"],
                        language=ep_row["language"],
                        duration_seconds=ep_row.get("duration_seconds"),
                        status=ep_row["status"],
                    )
                    session.add(ep)
                    await session.flush()

                    for art in ep_row.get("artwork", []):
                        session.add(
                            Artwork(
                                owner_type="episode",
                                owner_id=ep.id,
                                kind=art["kind"],
                                url=art["url"],
                                storage_key=art.get("file_name", art["url"]),
                                width=art["width"],
                                height=art["height"],
                                file_size_bytes=art["file_size_bytes"],
                                mime_type=art["mime_type"],
                            )
                        )

        await session.commit()


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_if_needed()


if __name__ == "__main__":
    asyncio.run(main())
