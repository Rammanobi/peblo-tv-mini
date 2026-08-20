import pytest

pytestmark = pytest.mark.asyncio


async def test_content_group_language_conflict_returns_409(client, editor_token):
    headers = {"Authorization": f"Bearer {editor_token}"}
    r = await client.post("/shows", headers=headers, json={"title": "CG Show", "category": "comedy"})
    show = r.json()
    r = await client.post(f"/shows/{show['id']}/seasons", headers=headers, json={"season_number": 1})
    season = r.json()

    r = await client.post(
        f"/seasons/{season['id']}/episodes",
        headers=headers,
        json={"title": "Ep A", "episode_number": 1, "content_group": "cg-1", "language": "en", "status": "draft"},
    )
    assert r.status_code == 201

    r2 = await client.post(
        f"/seasons/{season['id']}/episodes",
        headers=headers,
        json={"title": "Ep A dup", "episode_number": 2, "content_group": "cg-1", "language": "en", "status": "draft"},
    )
    assert r2.status_code == 409
    body = r2.json()
    assert body["error"]["type"] == "conflict"
    assert body["error"]["details"][0]["code"] == "CONTENT_GROUP_LANGUAGE_UNIQUE"


async def test_content_group_collapsing_produces_language_list(client, editor_token, admin_token):
    from tests.test_publish import _png_bytes

    headers = {"Authorization": f"Bearer {editor_token}"}
    r = await client.post(
        "/shows",
        headers=headers,
        json={"title": "Collapse Show", "category": "comedy", "section": "kids"},
    )
    show = r.json()
    for kind, w, h in [("poster", 600, 900), ("banner", 1280, 720)]:
        files = {"file": (f"{kind}.png", _png_bytes(w, h), "image/png")}
        await client.post(f"/shows/{show['id']}/artwork", headers=headers, data={"kind": kind}, files=files)
    r = await client.post(f"/shows/{show['id']}/seasons", headers=headers, json={"season_number": 1})
    season = r.json()

    ep_ids = []
    for lang in ["en", "hi"]:
        r = await client.post(
            f"/seasons/{season['id']}/episodes",
            headers=headers,
            json={
                "title": f"Ep 1 ({lang})",
                "episode_number": 1,
                "content_group": "collapse-s1-e01",
                "language": lang,
                "duration_seconds": 500,
                "status": "draft",
            },
        )
        assert r.status_code == 201, r.text
        ep = r.json()
        ep_ids.append(ep["id"])
        for kind, w, h in [("poster", 600, 900), ("banner", 1280, 720), ("thumbnail", 640, 360)]:
            files = {"file": (f"{kind}.png", _png_bytes(w, h), "image/png")}
            await client.post(f"/episodes/{ep['id']}/artwork", headers=headers, data={"kind": kind}, files=files)
        await client.patch(f"/episodes/{ep['id']}", headers=headers, json={"status": "published"})

    r = await client.get(f"/episodes/{ep_ids[0]}", headers=headers)
    variants = r.json()["variants"]
    assert any(v["language"] == "hi" for v in variants)
