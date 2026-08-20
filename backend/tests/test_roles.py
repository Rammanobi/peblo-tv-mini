import pytest

pytestmark = pytest.mark.asyncio


async def test_editor_forbidden_from_publish(client, editor_token):
    resp = await client.post(
        "/admin/catalog/publish",
        headers={"Authorization": f"Bearer {editor_token}"},
        json={},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["type"] == "forbidden"


async def test_admin_publish_blocked_by_seed_defect(client, admin_token):
    # The shipped seed fixture contains a deliberate CONTENT_GROUP_LANGUAGE_UNIQUE
    # duplicate (mango-and-moose / mm-s1-e04 / hi) which must block the whole
    # publish per docs/API_CONTRACT.md section 7's 422 example.
    resp = await client.post(
        "/admin/catalog/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["type"] == "validation_error"
    codes = {d["code"] for d in body["error"]["details"]}
    assert "CONTENT_GROUP_LANGUAGE_UNIQUE" in codes


async def test_missing_token_is_unauthorized(client):
    resp = await client.get("/shows")
    assert resp.status_code == 401


async def test_public_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
