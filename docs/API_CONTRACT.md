# Peblo TV Mini — REST API Contract v1

**Base URL:** `/api/v1` (all paths below are relative to it)
**Content type:** `application/json; charset=utf-8`, except artwork upload (`multipart/form-data`).
**Backend:** FastAPI + PostgreSQL. **Clients:** CMS (React, editor/admin) and Viewer (React, public).

This document is the single source of truth. Backend, CMS and Viewer implementers build
strictly against it. Enum values come from `data/reference.json`; the seed fixture and its
known defects are described in `data/SEED_NOTES.md`.

---

## 0. Conventions

### 0.1 Roles

| Role | Can do |
|---|---|
| _public_ (no token) | `GET /health`, `GET /catalog`, `GET /catalog/search` |
| `editor` | everything public + full CRUD on shows/seasons/episodes/artwork + `GET /admin/validation-report` |
| `admin` | everything an editor can do + `POST /admin/catalog/publish` |

Auth header: `Authorization: Bearer <jwt>`.

### 0.2 Error shape (universal)

Every 4xx/5xx response uses this envelope. Messages MUST be human-readable sentences an
editor can act on — never a bare code.

```jsonc
{
  "error": {
    "type": "validation_error",          // validation_error | not_found | conflict | unauthorized | forbidden | payload_too_large | internal_error
    "message": "This episode cannot be published yet. 2 problems must be fixed first.",
    "request_id": "req_01HTZ8Q4M9",
    "details": [
      {
        "code": "EPISODE_PUBLISHED_REQUIRES_ARTWORK",
        "field": "artwork.thumbnail",
        "message": "A published episode needs poster, banner and thumbnail artwork. The thumbnail (640x360) is missing.",
        "hint": "Upload a thumbnail via POST /episodes/41/artwork with kind=thumbnail, then publish again.",
        "resource": { "type": "episode", "id": 41, "title": "Feast of Forgotten Names" }
      },
      {
        "code": "EPISODE_PUBLISHED_REQUIRES_DURATION",
        "field": "duration_seconds",
        "message": "Duration is missing. A published episode must have a duration greater than 0 seconds.",
        "hint": "Set duration_seconds on the episode before publishing.",
        "resource": { "type": "episode", "id": 41, "title": "Feast of Forgotten Names" }
      }
    ]
  }
}
```

`details` is always an array (possibly empty). `field` uses dotted JSON paths into the
submitted body. Status codes: `400` malformed JSON, `401` missing/invalid token,
`403` wrong role, `404` not found, `409` uniqueness conflict, `413` file too large,
`422` validation failure, `500` internal.

### 0.3 Validation rules enforced by the API

| Code | Rule | Enforced at |
|---|---|---|
| `EPISODE_PUBLISHED_REQUIRES_DURATION` | published episode needs `duration_seconds > 0` (trailers exempt) | episode create/update, publish |
| `EPISODE_PUBLISHED_REQUIRES_ARTWORK` | published episode needs poster + banner + thumbnail | episode create/update, publish |
| `CONTENT_GROUP_LANGUAGE_UNIQUE` | `(content_group, language)` globally unique | episode create/update (`409`) |
| `CONTENT_GROUP_SINGLE_SHOW` | a `content_group` may not span shows | episode create/update (`409`) |
| `SHOW_PUBLISHED_REQUIRES_SECTION` | published show needs an allowed `section` | show create/update, publish |
| `SHOW_PUBLISHED_REQUIRES_ARTWORK` | published show needs poster + banner | show update, publish |
| `TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER` | season 0 rows must have `episode_number: null` | episode create/update |
| `EPISODE_NUMBER_UNIQUE_IN_SEASON` | `(season_id, episode_number, language)` unique for seasons ≥ 1 | episode create/update (`409`) |
| `ARTWORK_ASPECT_RATIO` | dimensions match the kind's ratio ±2% | artwork upload (`422`) |
| `ARTWORK_SIZE_LIMIT` | file ≤ 204800 bytes | artwork upload (`413`) |
| `ARTWORK_MIME_TYPE` | jpeg / png / webp only | artwork upload (`422`) |
| `ENUM_NOT_ALLOWED` | value absent from `reference.json` | any write (`422`) |

### 0.4 Pagination

List endpoints accept `?limit=` (default 50, max 200) and `?offset=` (default 0) and
return `{ "items": [...], "total": <int>, "limit": <int>, "offset": <int> }`.

---

## 1. Health

### `GET /health` — public

**200**
```json
{ "status": "ok", "version": "1.0.0", "database": "ok", "catalog_version": 7, "time": "2026-08-20T09:14:02Z" }
```
`catalog_version` is `null` until the first successful publish. Returns **503** with the
same body and `"status": "degraded"` if the database is unreachable.

---

## 2. Auth

### `POST /auth/login` — public

**Request**
```json
{ "email": "editor@peblo.tv", "password": "hunter2" }
```

**200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "id": 2, "email": "editor@peblo.tv", "name": "Ada Editor", "role": "editor" }
}
```

**JWT claims**
```json
{ "sub": "2", "email": "editor@peblo.tv", "role": "editor", "iat": 1755679200, "exp": 1755682800 }
```
`role` ∈ `editor | admin`. HS256, secret from `JWT_SECRET`. Clients must treat the token as
opaque apart from reading `role` and `exp` for UI gating.

**401**
```json
{ "error": { "type": "unauthorized", "message": "Email or password is incorrect.", "request_id": "req_...", "details": [] } }
```

### `GET /auth/me` — editor|admin
**200** → the `user` object above. **401** if the token is missing, expired or malformed.

---

## 3. Shows

### Show resource
```jsonc
{
  "id": 1,
  "slug": "pip-and-poms-puddle-park",
  "title": "Pip & Pom's Puddle Park",
  "description": "Two rain-loving friends turn every downpour into an adventure...",
  "category": "comedy",          // reference.json categories[].key
  "section": "kids",             // reference.json sections[].key, nullable while draft
  "status": "published",         // draft | published | archived
  "artwork": [ { "id": 10, "kind": "poster", "url": "https://cdn.peblo.tv/...", "width": 600, "height": 900, "file_size_bytes": 148213, "mime_type": "image/jpeg" } ],
  "season_count": 2,             // seasons >= 1 only (season 0 excluded)
  "episode_count": 12,           // non-trailer rows
  "trailer_count": 1,
  "created_at": "2026-07-01T10:00:00Z",
  "updated_at": "2026-08-19T16:22:11Z"
}
```

### `GET /shows` — editor|admin
Query: `status`, `section`, `category`, `q` (title substring), `limit`, `offset`.
**200** → paginated envelope of Show resources (without `seasons`).

### `POST /shows` — editor|admin
**Request** (`slug` auto-derived from `title` if omitted)
```json
{ "title": "Rocketmice", "slug": "rocketmice", "description": "A crew of pocket-sized astronauts...", "category": "adventure", "section": "kids", "status": "draft" }
```
**201** → Show resource. **422** on unknown enum values; **409** on duplicate `slug`:
```json
{ "error": { "type": "conflict", "message": "A show with the slug \"rocketmice\" already exists. Pick a different title or slug.", "request_id": "req_...", "details": [ { "code": "SHOW_SLUG_UNIQUE", "field": "slug", "message": "Slug \"rocketmice\" is taken by show #2.", "resource": { "type": "show", "id": 2 } } ] } }
```

### `GET /shows/{id}` — editor|admin
**200** → Show resource **plus** `"seasons": [ { "id", "season_number", "title", "episode_count" } ]`, season 0 included (the CMS must be able to manage trailers).

### `PATCH /shows/{id}` — editor|admin
Partial update; any subset of `title, slug, description, category, section, status`.
Setting `status: "published"` triggers `SHOW_PUBLISHED_REQUIRES_SECTION` and
`SHOW_PUBLISHED_REQUIRES_ARTWORK`:
```json
{ "error": { "type": "validation_error", "message": "\"Tiny Trekkers\" cannot be published yet. 1 problem must be fixed first.", "request_id": "req_...", "details": [ { "code": "SHOW_PUBLISHED_REQUIRES_SECTION", "field": "section", "message": "A published show must belong to a section. Choose one of: Kids, Family, Originals, Learning.", "hint": "PATCH /shows/6 with {\"section\": \"learning\"}.", "resource": { "type": "show", "id": 6, "title": "Tiny Trekkers" } } ] } }
```
**200** → updated Show resource.

### `DELETE /shows/{id}` — admin
Cascades to seasons, episodes and artwork. **204** no body.
**409** if the show appears in the currently published catalogue:
`"\"Rocketmice\" is live in catalogue version 7. Archive it and re-publish before deleting."`

---

## 4. Seasons

### Season resource
```json
{ "id": 3, "show_id": 2, "season_number": 1, "title": "Season 1", "is_trailer_season": false, "episode_count": 6 }
```
`is_trailer_season` is derived: `season_number == 0`.

### `GET /shows/{id}/seasons` — editor|admin
**200** → `{ "items": [Season], "total": 3, ... }`, ordered by `season_number` ascending
(season 0 first). Optional `?include_trailers=false` to omit season 0.

### `POST /shows/{id}/seasons` — editor|admin
```json
{ "season_number": 2, "title": "Season 2" }
```
**201** → Season. **409** if `(show_id, season_number)` exists:
`"Season 2 already exists for \"Rocketmice\"."`
`season_number` must be an integer ≥ 0; `0` is accepted and means the trailer season.

### `PATCH /seasons/{id}` — editor|admin — `{ "title": "..." }` (season_number immutable). **200** → Season.
### `DELETE /seasons/{id}` — admin — **204**; **409** if it still holds published episodes.

---

## 5. Episodes

### Episode resource
```jsonc
{
  "id": 41,
  "season_id": 3,
  "show_id": 2,
  "season_number": 1,
  "episode_number": 5,            // null for season-0 trailers
  "title": "Comet Courier",
  "synopsis": "A delivery must be made before the comet passes.",
  "content_group": "rm-s1-e05",   // shared by language variants of the same episode
  "language": "en",               // reference.json languages[].code
  "duration_seconds": 760,        // null allowed only while draft (trailers exempt)
  "status": "published",
  "is_trailer": false,            // derived: season_number == 0
  "artwork": [ { "id": 88, "kind": "thumbnail", "url": "...", "width": 640, "height": 360, "file_size_bytes": 74318, "mime_type": "image/jpeg" } ],
  "missing_artwork_kinds": [],    // convenience for the CMS badge
  "created_at": "2026-07-02T09:00:00Z",
  "updated_at": "2026-08-11T12:40:00Z"
}
```

### `GET /seasons/{id}/episodes` — editor|admin
Query: `language`, `status`, `limit`, `offset`.
**200** → paginated Episodes ordered by `episode_number ASC NULLS FIRST`, then `language`.

### `POST /seasons/{id}/episodes` — editor|admin
```json
{
  "title": "Comet Courier",
  "episode_number": 5,
  "content_group": "rm-s1-e05",
  "language": "en",
  "duration_seconds": 760,
  "synopsis": "A delivery must be made before the comet passes.",
  "status": "draft"
}
```
**201** → Episode.

**409 — duplicate variant**
```json
{ "error": { "type": "conflict", "message": "There is already a Hindi version of this episode.", "request_id": "req_...", "details": [ { "code": "CONTENT_GROUP_LANGUAGE_UNIQUE", "field": "language", "message": "Episode #77 (\"मैंगो का बड़ा आइडिया\") already uses content group \"mm-s1-e04\" with language \"hi\". Each content group may have only one row per language.", "hint": "Edit episode #77 instead, or give this row a different content_group.", "resource": { "type": "episode", "id": 77 } } ] } }
```

**422 — trailer with an episode number**
```json
{ "error": { "type": "validation_error", "message": "Trailers cannot have an episode number.", "request_id": "req_...", "details": [ { "code": "TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER", "field": "episode_number", "message": "This episode is in season 0, which is reserved for trailers. Season 0 rows must leave episode_number empty.", "hint": "Send episode_number: null, or move the episode to season 1 or later.", "resource": { "type": "episode", "id": null, "title": "Puddle Park - Season 1 Trailer" } } ] } }
```

### `GET /episodes/{id}` — editor|admin — **200** → Episode, plus
`"variants": [ { "id": 42, "language": "hi", "title": "...", "status": "published" } ]` (the other rows sharing its `content_group`).

### `PATCH /episodes/{id}` — editor|admin
Any subset of `title, episode_number, content_group, language, duration_seconds, synopsis, status`.
Publishing (`status: "published"`) runs the duration + artwork checks and returns **422**
with one `details` entry per missing piece (see §0.2).

### `DELETE /episodes/{id}` — editor|admin — **204**. Deleting one language variant leaves the rest intact.

---

## 6. Artwork

Multipart upload. Field `file` is the binary; `kind` is a form field.
Re-uploading the same `kind` **replaces** the existing artwork for that resource.

### `POST /episodes/{id}/artwork` — editor|admin
`Content-Type: multipart/form-data`

| Part | Type | Notes |
|---|---|---|
| `kind` | text | `poster` \| `banner` \| `thumbnail` |
| `file` | file | jpeg/png/webp, ≤ 204800 bytes |
| `alt_text` | text | optional |

**201**
```json
{ "id": 88, "episode_id": 41, "kind": "thumbnail", "url": "https://cdn.peblo.tv/artwork/rocketmice-s1e05-thumbnail.jpg", "width": 640, "height": 360, "aspect_ratio": "16:9", "file_size_bytes": 74318, "mime_type": "image/jpeg", "alt_text": null, "created_at": "2026-08-20T09:02:00Z" }
```

**413 — too large**
```json
{ "error": { "type": "payload_too_large", "message": "That banner is too big.", "request_id": "req_...", "details": [ { "code": "ARTWORK_SIZE_LIMIT", "field": "file", "message": "The file is 262 KB. Artwork must be 200 KB or smaller.", "hint": "Re-export the image as JPEG at ~80% quality, or use WebP." } ] } }
```

**422 — wrong aspect ratio / mime**
```json
{ "error": { "type": "validation_error", "message": "That poster is the wrong shape.", "request_id": "req_...", "details": [ { "code": "ARTWORK_ASPECT_RATIO", "field": "file", "message": "Posters must be 2:3 (about 600x900). The uploaded image is 800x900, which is 8:9.", "hint": "Crop or re-export at 600x900 and upload again." } ] } }
```

### `GET /episodes/{id}/artwork` — editor|admin
**200** → `{ "items": [Artwork], "missing_kinds": ["thumbnail"] }`

### `DELETE /artwork/{artwork_id}` — editor|admin
**204**; **409** if removing it would leave a *published* episode/show incomplete:
`"\"Comet Courier\" is published and needs a thumbnail. Unpublish the episode or upload a replacement first."`

### `POST /shows/{id}/artwork` — editor|admin
Same contract; `kind` restricted to `poster` | `banner` (show hero/poster). **201** returns
the same object with `show_id` in place of `episode_id`.

### `GET /shows/{id}/artwork` — editor|admin — as above.

---

## 7. Publishing

### `POST /admin/catalog/publish` — **admin only**

Builds `catalogue.json` from all `published` shows and episodes, collapsing `content_group`
variants and excluding season 0 from season lists. Runs the full validation pass first.

**Request** (body optional)
```json
{ "dry_run": false, "note": "Aug launch batch" }
```

**200 — success**
```jsonc
{
  "run_id": "pub_01HTZ9F3K7QW",
  "status": "success",              // success | success_with_warnings | blocked
  "version": 7,                     // monotonically increasing catalogue version
  "published_at": "2026-08-20T09:14:02Z",
  "published_by": { "id": 1, "email": "admin@peblo.tv" },
  "duration_ms": 412,
  "note": "Aug launch batch",
  "counts": {
    "sections": 4,
    "shows": 5,
    "catalog_entries": 44,          // after content_group collapsing
    "episode_rows_considered": 61,
    "rows_collapsed": 17,           // rows merged into an existing entry
    "trailers": 5,
    "languages": { "en": 44, "hi": 7, "es": 6 },
    "skipped_shows": 1,
    "skipped_episodes": 3
  },
  "warnings": [
    { "code": "SHOW_SKIPPED", "message": "\"Tiny Trekkers\" was skipped: a published show must belong to a section.", "resource": { "type": "show", "id": 6 } }
  ],
  "catalog_url": "/api/v1/catalog"
}
```

**422 — blocked by validation** (`status: "blocked"`, nothing published, previous version stays live)
```json
{ "error": { "type": "validation_error", "message": "Publish blocked. 7 issues across 7 shows must be fixed first.", "request_id": "req_...", "details": [ { "code": "CONTENT_GROUP_LANGUAGE_UNIQUE", "field": "content_group", "message": "Content group \"mm-s1-e04\" has two Hindi rows (episodes #77 and #95). It cannot be collapsed into one catalogue entry.", "resource": { "type": "show", "id": 7, "title": "Mango & Moose" } } ] } }
```
**403** if the caller's role is `editor`:
`"Publishing the catalogue requires an admin account. Ask an admin to run the publish."`

`dry_run: true` returns the identical success body with `"version": null` and
`"dry_run": true`, and writes nothing.

### `GET /admin/catalog/publish-runs` — editor|admin
**200** → paginated history: `{ "run_id", "status", "version", "published_at", "published_by", "counts", "warning_count" }`.

---

## 8. Catalogue (public — the Viewer reads ONLY these)

### `GET /catalog` — public

Serves the most recent successful publish. Grouped by section; navigation sections only
(`trailers` is never a group). Cache: `ETag` + `Cache-Control: public, max-age=60`.

```jsonc
{
  "catalog_version": 7,
  "generated_at": "2026-08-20T09:14:02Z",
  "reference_version": "1.0.0",
  "languages": ["en", "hi", "es"],
  "sections": [
    {
      "key": "kids",
      "label": "Kids",
      "sort_order": 1,
      "shows": [
        {
          "id": 1,
          "slug": "pip-and-poms-puddle-park",
          "title": "Pip & Pom's Puddle Park",
          "description": "Two rain-loving friends turn every downpour into an adventure...",
          "category": "comedy",
          "category_label": "Comedy",
          "languages": ["en", "hi"],           // union across all entries
          "artwork": { "poster": { "url": "...", "width": 600, "height": 900 },
                       "banner": { "url": "...", "width": 1280, "height": 720 } },
          "seasons": [                          // season 0 NEVER appears here
            {
              "season_number": 1,
              "title": "Season 1",
              "episode_count": 8,
              "episodes": [
                {
                  "content_group": "pp-s1-e01",  // stable id of the collapsed entry
                  "episode_number": 1,
                  "title": "Puddle Trouble",
                  "synopsis": "Pip loses a boot in the deepest puddle in the park.",
                  "duration_seconds": 665,
                  "languages": ["en", "hi"],     // collapsed language variants, default first
                  "titles_by_language": { "en": "Puddle Trouble", "hi": "पड़ोसी पुडल" },
                  "artwork": { "poster": { "url": "...", "width": 600, "height": 900 },
                               "banner": { "url": "...", "width": 1280, "height": 720 },
                               "thumbnail": { "url": "...", "width": 640, "height": 360 } }
                }
              ]
            }
          ],
          "trailers": [                          // season 0 surfaces ONLY here
            { "content_group": "pp-tr-01", "title": "Puddle Park - Season 1 Trailer",
              "duration_seconds": 62, "languages": ["en"],
              "artwork": { "thumbnail": { "url": "...", "width": 640, "height": 360 } } }
          ]
        }
      ]
    }
  ]
}
```

Guarantees the Viewer may rely on:
1. Every `shows[].seasons[].season_number` is ≥ 1.
2. Every episode entry is unique by `content_group` within the response.
3. `languages` is non-empty, deduplicated, and ordered default-language first.
4. Every published entry has all three artwork kinds; every show has poster + banner.
5. `sections[]` contains only sections with `show_in_nav: true`, in `sort_order`.

**404** before the first successful publish:
```json
{ "error": { "type": "not_found", "message": "No catalogue has been published yet. An admin must run a publish first.", "request_id": "req_...", "details": [] } }
```

### `GET /catalog/search` — public

Query params (all optional, AND-combined; omitting all returns everything):

| Param | Type | Meaning |
|---|---|---|
| `q` | string | case-insensitive substring over show title, episode title (any language) and synopsis |
| `category` | enum key | `comedy \| adventure \| educational \| music \| fantasy \| nature` |
| `language` | enum code | `en \| hi \| es` — matches entries whose `languages` array contains it |
| `section` | enum key | nav sections only |
| `limit` / `offset` | int | default 50 / 0 |

Searches the published catalogue only (never the database), and never returns season-0 rows.

**200**
```jsonc
{
  "query": { "q": "puddle", "category": null, "language": "hi", "section": "kids" },
  "catalog_version": 7,
  "total": 2,
  "limit": 50,
  "offset": 0,
  "results": [
    {
      "type": "episode",                       // "show" | "episode"
      "content_group": "pp-s1-e01",
      "title": "Puddle Trouble",
      "synopsis": "Pip loses a boot in the deepest puddle in the park.",
      "duration_seconds": 665,
      "languages": ["en", "hi"],
      "season_number": 1,
      "episode_number": 1,
      "show": { "id": 1, "slug": "pip-and-poms-puddle-park", "title": "Pip & Pom's Puddle Park", "section": "kids", "category": "comedy" },
      "artwork": { "thumbnail": { "url": "...", "width": 640, "height": 360 } },
      "matched_on": ["title"]
    }
  ]
}
```

**422** on an unknown enum value:
```json
{ "error": { "type": "validation_error", "message": "\"fr\" is not a supported language.", "request_id": "req_...", "details": [ { "code": "ENUM_NOT_ALLOWED", "field": "language", "message": "Supported languages are: en (English), hi (Hindi), es (Spanish).", "hint": "Remove the language filter or use one of the supported codes." } ] } }
```

---

## 9. Validation report

### `GET /admin/validation-report` — editor|admin

Runs the same checks as publish, against the live database, without publishing. The CMS
shows this as a pre-flight checklist; against the shipped seed it must return exactly the
seven issues listed in `data/SEED_NOTES.md`.

Query: `?show_id=` to scope to one show, `?severity=blocking|warning`.

**200**
```jsonc
{
  "generated_at": "2026-08-20T09:10:44Z",
  "publishable": false,
  "summary": {
    "blocking_issues": 7,
    "warnings": 0,
    "shows_affected": 7,
    "shows_total": 8,
    "by_type": {
      "EPISODE_PUBLISHED_REQUIRES_DURATION": 1,
      "EPISODE_PUBLISHED_REQUIRES_ARTWORK": 1,
      "CONTENT_GROUP_LANGUAGE_UNIQUE": 1,
      "SHOW_PUBLISHED_REQUIRES_SECTION": 1,
      "TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER": 1,
      "ARTWORK_ASPECT_RATIO": 1,
      "ARTWORK_SIZE_LIMIT": 1
    }
  },
  "by_show": [
    {
      "show": { "id": 2, "slug": "rocketmice", "title": "Rocketmice", "status": "published", "section": "kids" },
      "blocking_count": 1,
      "warning_count": 0,
      "issues": [
        {
          "code": "EPISODE_PUBLISHED_REQUIRES_DURATION",
          "severity": "blocking",
          "message": "\"Silent Signal\" (S2E3) is published but has no duration.",
          "hint": "Set duration_seconds on episode #29, or move it back to draft.",
          "resource": { "type": "episode", "id": 29, "title": "Silent Signal", "season_number": 2, "episode_number": 3, "language": "en", "content_group": "rm-s2-e03" },
          "field": "duration_seconds"
        }
      ]
    },
    {
      "show": { "id": 7, "slug": "mango-and-moose", "title": "Mango & Moose", "status": "published", "section": "originals" },
      "blocking_count": 1,
      "warning_count": 0,
      "issues": [
        {
          "code": "CONTENT_GROUP_LANGUAGE_UNIQUE",
          "severity": "blocking",
          "message": "Content group \"mm-s1-e04\" has two Hindi rows, so it cannot be collapsed into a single catalogue entry.",
          "hint": "Delete or re-language episode #95, or give it its own content_group.",
          "resource": { "type": "episode", "id": 95, "title": "मैंगो का बड़ा आइडिया (नया डब)", "language": "hi", "content_group": "mm-s1-e04" },
          "related": [ { "type": "episode", "id": 77, "title": "मैंगो का बड़ा आइडिया" } ],
          "field": "content_group"
        }
      ]
    }
  ]
}
```

When everything is clean: `"publishable": true`, `"by_show": []`, all summary counts `0`.

---

## 10. Endpoint index

| Method | Path | Auth |
|---|---|---|
| GET | `/health` | public |
| POST | `/auth/login` | public |
| GET | `/auth/me` | editor+ |
| GET | `/shows` | editor+ |
| POST | `/shows` | editor+ |
| GET | `/shows/{id}` | editor+ |
| PATCH | `/shows/{id}` | editor+ |
| DELETE | `/shows/{id}` | admin |
| GET | `/shows/{id}/seasons` | editor+ |
| POST | `/shows/{id}/seasons` | editor+ |
| PATCH | `/seasons/{id}` | editor+ |
| DELETE | `/seasons/{id}` | admin |
| GET | `/seasons/{id}/episodes` | editor+ |
| POST | `/seasons/{id}/episodes` | editor+ |
| GET | `/episodes/{id}` | editor+ |
| PATCH | `/episodes/{id}` | editor+ |
| DELETE | `/episodes/{id}` | editor+ |
| GET/POST | `/episodes/{id}/artwork` | editor+ |
| GET/POST | `/shows/{id}/artwork` | editor+ |
| DELETE | `/artwork/{id}` | editor+ |
| POST | `/admin/catalog/publish` | **admin** |
| GET | `/admin/catalog/publish-runs` | editor+ |
| GET | `/admin/validation-report` | editor+ |
| GET | `/catalog` | public |
| GET | `/catalog/search` | public |
