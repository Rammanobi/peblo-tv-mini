from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.errors import register_error_handlers
from app.routers import admin, artwork, auth, catalog, episodes, health, seasons, shows


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.auto_seed:
        from scripts.seed import seed_if_needed

        await seed_if_needed()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Peblo TV Mini API", version=settings.app_version, lifespan=lifespan)
    register_error_handlers(app)

    # The Viewer and CMS are separate origins (different ports) in dev and
    # separate subdomains in production — the browser enforces CORS on every
    # fetch, so the API must explicitly allow the origins that are meant to
    # call it. CORS_ORIGIN is a comma-separated list; unset falls back to the
    # conventional local dev ports for both frontends.
    allowed_origins = [
        origin.strip()
        for origin in settings.cors_origin.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Local-disk storage writes real files to disk, but nothing served them
    # over HTTP — every artwork url_for() pointed at STORAGE_PUBLIC_BASE_URL,
    # which was a dead route. Mount the storage directory at that same path
    # so uploaded artwork actually loads in the browser. Only relevant for
    # the local backend: S3/R2 serve files from the bucket/CDN directly, so
    # there's nothing to mount when STORAGE_BACKEND=s3.
    if settings.storage_backend == "local":
        from pathlib import Path
        from urllib.parse import urlparse

        mount_path = urlparse(settings.storage_public_base_url).path or "/static/artwork"
        Path(settings.storage_local_dir).mkdir(parents=True, exist_ok=True)
        app.mount(mount_path, StaticFiles(directory=settings.storage_local_dir), name="artwork")

    api = APIRouter(prefix="/api/v1")
    api.include_router(health.router)
    api.include_router(auth.router)
    api.include_router(shows.router)
    api.include_router(seasons.router)
    api.include_router(episodes.router)
    api.include_router(artwork.router)
    api.include_router(admin.router)
    api.include_router(catalog.router)
    app.include_router(api)
    return app


app = create_app()
