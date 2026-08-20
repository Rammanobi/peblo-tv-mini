# SEED_NOTES.md — answer key for `seed_shows.json`

`data/seed_shows.json` is a **deliberately imperfect** fixture. It contains 8 shows,
18 season records (10 numbered seasons + 8 trailer seasons) and **95 episode rows** (trailers and language variants included).

A correct implementation of `GET /admin/validation-report` must surface **exactly the
seven defects below** as blocking issues, and `POST /admin/catalog/publish` must exclude
(or refuse to publish) the affected rows rather than emitting a broken catalogue.

Row identifiers below use the form `show_slug / S<season>E<episode> [language]`, or the
row's `content_group` where the episode number is ambiguous.

---

## D1 — Published episode with no duration
- **Row:** `rocketmice / S2E3 "Silent Signal" [en]` (`content_group: rm-s2-e03`)
- **Defect:** `status: "published"` but `duration_seconds: null`.
- **Rule violated:** `EPISODE_PUBLISHED_REQUIRES_DURATION`
- **Why it matters:** the Viewer renders a runtime badge and a progress bar from
  `duration_seconds`. A null duration produces `NaN` in the UI and breaks resume logic.
  This is the classic "editor hit Publish before the transcode metadata landed" case.

## D2 — Published episode missing required artwork
- **Row:** `the-wobbly-kingdom / S1E5 "Feast of Forgotten Names" [en]` (`wk-s1-e05`)
- **Defect:** only `poster` and `banner` artwork present; **`thumbnail` is absent**.
- **Rule violated:** `EPISODE_PUBLISHED_REQUIRES_ARTWORK`
- **Why it matters:** all three shapes are required for a published episode. Without a
  thumbnail the episode list row renders an empty tile. The validation report must name
  the *missing kind*, not just say "artwork invalid".

## D3 — Duplicate `(content_group, language)` pair
- **Rows:** `mango-and-moose / S1E4 [hi]` appears **twice** —
  `"मैंगो का बड़ा आइडिया"` (1124s) and `"मैंगो का बड़ा आइडिया (नया डब)"` (1124s),
  both with `content_group: mm-s1-e04`, `language: "hi"`.
- **Rule violated:** `CONTENT_GROUP_LANGUAGE_UNIQUE`
- **Why it matters:** the publish job collapses a `content_group` into ONE catalogue entry
  with a `languages` array. Two rows for the same language make the collapse
  non-deterministic (which Hindi asset wins?) and would emit `["en","hi","hi"]`. This is
  the single most important defect in the fixture — it directly tests the collapsing logic.

## D4 — Published show with no section
- **Row:** show `tiny-trekkers` ("Tiny Trekkers")
- **Defect:** `status: "published"` but `section: null`.
- **Rule violated:** `SHOW_PUBLISHED_REQUIRES_SECTION`
- **Why it matters:** `GET /catalog` groups strictly by section. A sectionless published
  show has nowhere to live — it either disappears silently or crashes the grouping step.
  All 8 of its episode rows are collateral: none can reach the Viewer.

## D5 — Trailer (season 0) carrying a season episode number
- **Row:** `pip-and-poms-puddle-park / S0 "Puddle Park - Season 1 Trailer"` (`pp-tr-01`)
- **Defect:** `episode_number: 1` on a season-0 row (should be `null`).
- **Rule violated:** `TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER`
- **Why it matters:** season 0 is reserved for trailers and is excluded from the normal
  season list. A numbered trailer leaks into "Episode 1" sort positions and can shadow the
  real S1E1 in any code that keys on `(season_number, episode_number)` carelessly.

## D6 — Artwork with the wrong aspect ratio
- **Row:** show `counting-with-coco`, show-level `poster` artwork
- **Defect:** dimensions `800 × 900` (ratio 0.889) where the poster spec requires
  `600 × 900` / **2:3** (ratio 0.667).
- **Rule violated:** `ARTWORK_ASPECT_RATIO`
- **Why it matters:** posters sit in a fixed 2:3 rail. An 8:9 image is either letterboxed
  or cropped through the character's face. Aspect must be validated at upload, not at render.

## D7 — Artwork over the 200 KB ceiling
- **Row:** `banjo-street-band / S1E8 "Festival Finale" [en]` (`bb-s1-e08`), `banner` artwork
- **Defect:** `file_size_bytes: 268431` (262 KB) vs the 204800-byte ceiling.
- **Rule violated:** `ARTWORK_SIZE_LIMIT`
- **Why it matters:** the ceiling exists so the Viewer's section rails stay fast on mobile.
  The error message must quote both the actual size and the limit in human units.

---

## Deliberately *valid* things that look like defects (do not flag)

These exist to catch over-eager validators:

| Looks wrong | Actually fine because |
|---|---|
| Many rows share a `content_group` (e.g. `pp-s1-e01` has `en` + `hi`) | That is the language-variant mechanism. Only same-language duplicates are errors. |
| Trailers have no `episode_number` | Correct convention for season 0. |
| `nightlight-tales` is `draft` and all its episodes are `draft` | Draft content is exempt from publish-time rules and simply never reaches `/catalog`. |
| Trailers are 30–90 seconds long | Trailers are exempt from any episode-length expectation. |
| `mango-and-moose` season 0 has **two** trailers | A show may have multiple trailers. |
| `rocketmice` has seasons 1 and 2 with overlapping episode numbers | Episode numbers are unique per season, not per show. |

## Expected validation-report summary (target output)

```
blocking_issues: 7
by_type:
  EPISODE_PUBLISHED_REQUIRES_DURATION   1   (rocketmice)
  EPISODE_PUBLISHED_REQUIRES_ARTWORK    1   (the-wobbly-kingdom)
  CONTENT_GROUP_LANGUAGE_UNIQUE         1   (mango-and-moose)
  SHOW_PUBLISHED_REQUIRES_SECTION       1   (tiny-trekkers)
  TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER  1   (pip-and-poms-puddle-park)
  ARTWORK_ASPECT_RATIO                  1   (counting-with-coco)
  ARTWORK_SIZE_LIMIT                    1   (banjo-street-band)
```

Seven distinct shows, seven distinct rule codes — one clean defect per show except
`nightlight-tales` (all-draft, intentionally clean).
