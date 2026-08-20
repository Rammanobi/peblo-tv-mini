import pytest

pytestmark = pytest.mark.asyncio


async def test_seed_validation_report_has_seven_defects(client, editor_token):
    headers = {"Authorization": f"Bearer {editor_token}"}
    r = await client.get("/admin/validation-report", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["publishable"] is False
    assert body["summary"]["blocking_issues"] == 7
    expected_codes = {
        "EPISODE_PUBLISHED_REQUIRES_DURATION",
        "EPISODE_PUBLISHED_REQUIRES_ARTWORK",
        "CONTENT_GROUP_LANGUAGE_UNIQUE",
        "SHOW_PUBLISHED_REQUIRES_SECTION",
        "TRAILER_MUST_NOT_HAVE_EPISODE_NUMBER",
        "ARTWORK_ASPECT_RATIO",
        "ARTWORK_SIZE_LIMIT",
    }
    assert set(body["summary"]["by_type"].keys()) == expected_codes
    assert all(v == 1 for v in body["summary"]["by_type"].values())
