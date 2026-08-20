import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


def _normalize_database_url(url: str) -> str:
    # SQLAlchemy's create_async_engine needs an async driver in the URL scheme.
    # DATABASE_URL is commonly supplied as plain postgresql:// (e.g. by
    # docker-compose or a hosting platform) — rewrite it to use asyncpg rather
    # than requiring every caller to know the async-driver convention.
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    return url


class Settings:
    database_url: str = _normalize_database_url(
        os.environ.get(
            "DATABASE_URL",
            f"sqlite+aiosqlite:///{(BACKEND_DIR / 'peblo.db').as_posix()}",
        )
    )
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-secret-change-me")
    cors_origin: str = os.environ.get(
        "CORS_ORIGIN", "http://localhost:3000,http://localhost:3001"
    )
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = int(os.environ.get("JWT_EXPIRES_SECONDS", "3600"))
    storage_backend: str = os.environ.get("STORAGE_BACKEND", "local")
    storage_local_dir: str = os.environ.get(
        "STORAGE_LOCAL_DIR", (BACKEND_DIR / "storage_data").as_posix()
    )
    storage_public_base_url: str = os.environ.get(
        "STORAGE_PUBLIC_BASE_URL", "https://cdn.peblo.tv/artwork"
    )
    s3_bucket: str = os.environ.get("S3_BUCKET", "peblo-artwork")
    s3_endpoint_url: str | None = os.environ.get("S3_ENDPOINT_URL")
    s3_region: str = os.environ.get("S3_REGION", "us-east-1")
    s3_access_key: str | None = os.environ.get("AWS_ACCESS_KEY_ID")
    s3_secret_key: str | None = os.environ.get("AWS_SECRET_ACCESS_KEY")
    reference_path: str = os.environ.get(
        "REFERENCE_PATH", (PROJECT_ROOT / "data" / "reference.json").as_posix()
    )
    seed_path: str = os.environ.get(
        "SEED_PATH", (PROJECT_ROOT / "data" / "seed_shows.json").as_posix()
    )
    catalog_dir: str = os.environ.get(
        "CATALOG_DIR", (BACKEND_DIR / "storage_data" / "catalog").as_posix()
    )
    app_version: str = "1.0.0"
    auto_seed: bool = os.environ.get("AUTO_SEED", "true").lower() == "true"


settings = Settings()
