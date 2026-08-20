import os
import sys
import tempfile
from pathlib import Path

TEST_DIR = Path(tempfile.mkdtemp(prefix="peblo-test-"))
BACKEND_DIR = Path(__file__).resolve().parent.parent

os.environ["DATABASE_URL"] = os.environ.get("PEBLO_TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_DIR"] = (TEST_DIR / "storage").as_posix()
os.environ["CATALOG_DIR"] = (TEST_DIR / "catalog").as_posix()
os.environ["AUTO_SEED"] = "false"
os.environ["REFERENCE_PATH"] = (BACKEND_DIR.parent / "data" / "reference.json").as_posix()
os.environ["SEED_PATH"] = (BACKEND_DIR.parent / "data" / "seed_shows.json").as_posix()

sys.path.insert(0, str(BACKEND_DIR))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

import app.database as db_module
from app.database import Base
from app.main import create_app
from scripts.seed import seed_if_needed


@pytest_asyncio.fixture
async def app():
    # asyncpg binds its connection pool to whichever event loop first used
    # it. pytest-asyncio gives each test function its own event loop, so
    # reusing the module-level `engine` singleton across tests breaks against
    # real Postgres ("attached to a different loop") even though aiosqlite
    # tolerates it silently. Dispose and rebuild the engine fresh for every
    # test so its pool is always bound to *this* test's running loop —
    # this mirrors how the real app only ever creates one engine per
    # process/event-loop lifetime, it just does it once per test here.
    old_engine = db_module.engine
    await old_engine.dispose()
    connect_args = {"check_same_thread": False} if db_module.settings.database_url.startswith("sqlite") else {}
    new_engine = create_async_engine(db_module.settings.database_url, echo=False, connect_args=connect_args)
    db_module.engine = new_engine
    db_module.SessionLocal.configure(bind=new_engine)

    async with new_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed_if_needed()
    application = create_app()
    try:
        yield application
    finally:
        await new_engine.dispose()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac


async def _login(client, email, password):
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client):
    return await _login(client, "admin@peblo.tv", "admin123")


@pytest_asyncio.fixture
async def editor_token(client):
    return await _login(client, "editor@peblo.tv", "hunter2")
