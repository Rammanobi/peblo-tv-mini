# DECISIONS.md — Peblo TV Mini backend

Ambiguous calls made while implementing against `docs/API_CONTRACT.md`, and the
reasoning behind each.

## 1. Publish: which failures block vs. skip-and-continue

The contract's prose (section 7) says publish "skips shows/episodes that fail
validation" but its own 422 "blocked" example uses `CONTENT_GROUP_LANGUAGE_UNIQUE`
as the blocking reason. These two statements are only reconcilable if different
rule violations get different treatment. The decision made here:

- `CONTENT_GROUP_LANGUAGE_UNIQUE` **blocks the entire publish** (422, nothing
  written, previous version stays live). Rationale: it makes the content-group
  collapse non-deterministic — there is no principled way to pick a "winner"
  automatically, and silently dropping one row would non-deterministically hide
  data. This matches the contract's own 422 example verbatim.
- `SHOW_PUBLISHED_REQUIRES_SECTION`, `SHOW_PUBLISHED_REQUIRES_ARTWORK`,
  `EPISODE_PUBLISHED_REQUIRES_DURATION`, `EPISODE_PUBLISHED_REQUIRES_ARTWORK`,
  and `TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER` are **skip-and-continue**: the
  affected show/episode is left out of the catalogue, counted in
  `skipped_shows`/`skipped_episodes`, and reported via `warnings[]` with status
  `success_with_warnings`. This matches SEED_NOTES.md's "must exclude ... the
  affected rows rather than emitting a broken catalogue" for D1/D2/D4/D5.

Because the shipped seed fixture always contains the D3 duplicate
(`mango-and-moose` / `mm-s1-e04` / `hi`), `POST /admin/catalog/publish` against
an untouched seed database always returns 422 blocked until that row is fixed
or deleted. This is intentional and is exercised by
`backend/tests/test_roles.py::test_admin_publish_blocked_by_seed_defect`.

## 2. `(content_group, language)` uniqueness is NOT a DB constraint

The contract lists `UNIQUE(content_group, language)` as a desired DB
constraint. The shipped seed fixture (`data/seed_shows.json`) intentionally
contains a duplicate pair (defect D3) so the validation report / publish job
can demonstrate detecting it. A real DB unique constraint would make the seed
script fail to load. Uniqueness for `(content_group, language)` is therefore
enforced only at the app/service layer
(`app/routers/episodes.py::_check_content_group_conflicts`, and the full-scan
version in `app/services/validation.py`), returning `409` on write and
appearing as a blocking issue in the validation report / publish. See
`app/models.py` for an inline comment at the same spot.

All other constraints from the contract *are* real DB constraints:
`UNIQUE(slug)` on shows, `UNIQUE(show_id, season_number)` on seasons,
`UNIQUE(owner_type, owner_id, kind)` on artwork, and a partial
`UNIQUE(status) WHERE status='running'` on `publish_runs`.

## 3. `SHOW_PUBLISHED_REQUIRES_SECTION` as an app-layer rule, not a DB CHECK

`section` is a nullable FK-like string column (no real FK table — sections
live in `reference.json`, not the DB) validated against the enum at the app
layer. A `published` show requiring a non-null `section` therefore can't be a
DB CHECK without either a trigger or making `section` non-nullable (which
would break drafts). It's enforced in `app/routers/shows.py::_check_publish_requirements`
and in the validation report / publish service.

## 4. Search implementation and its scale ceiling

`GET /catalog/search` loads the last-published `catalogue.json` from storage
and filters it in pure Python (`app/services/catalog_read.py`). This satisfies
the contract's "searches the published catalogue only" requirement exactly and
needs no additional index/table. It is O(entries) per request with no
pagination pushdown — the whole matching set is materialized in memory before
slicing `limit`/`offset`. This is fine for the seed's ~44 catalogue entries and
comfortably up to a few thousand; past roughly 10k–50k entries (depending on
request volume) this should move to a Postgres table of flattened catalogue
rows with a GIN/trigram index on title/synopsis, populated by the publish job
alongside the JSON file.

## 5. Publish idempotency

`POST /admin/catalog/publish` computes a stable hash of the built catalogue
(sorted-keys JSON, excluding `generated_at`/`catalog_version`). If it matches
the hash of the last successful run, no new versioned file is written and no
pointer flip happens — but a `publish_runs` row is still recorded (with the
existing version number) so the run history is a complete audit trail even for
no-op republishes. This was not spelled out in the contract; the "atomic
write-new-versioned-key-then-flip-pointer" description implies a new version
per *change*, not per *call*.

## 6. Storage layout

`LocalDiskStorage` writes under `backend/storage_data/`. Artwork keys are
`{owner_type}/{owner_id}/{kind}-{random8hex}.{ext}`; catalogue files are
`catalog/catalogue.v{N}.json` plus a `catalog/pointer.json` that is the only
thing rewritten atomically (temp file + `os.replace`) to "flip" to a new
version — the versioned files themselves are never overwritten once written.
`S3Storage` mirrors the same key scheme against an S3-compatible bucket
(works with MinIO/R2 via `S3_ENDPOINT_URL`) but is unexercised in this
environment (no live S3/MinIO endpoint available) — it is structurally
complete and swappable via `STORAGE_BACKEND=s3`, but only `LocalDiskStorage`
has been run.

## 7. SQLite-vs-Postgres divergence for tests

The suite defaults to SQLite (`aiosqlite`) for fast, isolated local runs, but
has since been run against a real Postgres 16 instance (the same
`docker-compose` service) and **all 13 tests pass unmodified** — set
`PEBLO_TEST_DATABASE_URL` to a `postgresql+asyncpg://...` URL before running
`pytest` to reproduce (see `backend/tests/conftest.py`).

Running against real Postgres surfaced one genuine bug that SQLite masked:
`tests/conftest.py` originally reused one module-level SQLAlchemy `engine`
across every test. `aiosqlite` tolerates that being reused across
pytest-asyncio's per-test event loops; `asyncpg` does not — it binds its
connection pool to the event loop that first touched it and raises
`InterfaceError: another operation is in progress` (or, once loop scoping
was patched, `RuntimeError: ... attached to a different loop`) the moment a
second test's loop tries to reuse it. Fixed by disposing and rebuilding the
engine fresh inside the `app` fixture for every test, so its pool is always
bound to that test's currently-running loop — this is a test-fixture
concern only, not a production one (the real app creates one engine once,
inside uvicorn's single long-lived loop).

Remaining (non-blocking) divergences between the two dialects:

- The partial unique index on `publish_runs(status) WHERE status='running'`
  is created via SQLAlchemy's `sqlite_where=`/`postgresql_where=` on the same
  `Index` definition, exercised in both dialects.
- `BigInteger` behaves as SQLite's dynamically-typed `INTEGER` rather than a
  fixed 8-byte column under the SQLite path — inconsequential at this data
  scale, and moot when running against Postgres.
- No native Postgres `ENUM` types are used anywhere (roles/categories/sections
  etc. are plain `VARCHAR` validated against `reference.json` at the app
  layer), so there is no divergence there to begin with.
- Alembic's `alembic/versions/0001_initial.py` targets Postgres-flavored DDL
  (asyncpg) as the "real" migration and has been applied against the live
  `docker-compose` Postgres via the API container's startup entrypoint; the
  SQLite test path still bypasses Alembic and calls
  `Base.metadata.create_all()` directly for speed and isolation.

## 8. Auth / seed users

Seed users are `admin@peblo.tv` / `admin123` (admin) and `editor@peblo.tv` /
`hunter2` (editor) — the editor credentials match the contract's own
`POST /auth/login` example exactly; the admin password was invented since the
contract doesn't specify one.

## 9. `DELETE /shows/{id}` live-catalogue check

The contract says deleting a show that "appears in the currently published
catalogue" should 409. Rather than re-parsing the published `catalogue.json`
on every delete, this is approximated by checking the show's own `status`
(if it's currently `published` and at least one successful publish run
exists, block the delete). This is a conservative approximation — it will
occasionally block deletes of a `published` show that was actually skipped
from the last publish (e.g. still missing artwork) — documented here rather
than silently accepted as exactly correct.
