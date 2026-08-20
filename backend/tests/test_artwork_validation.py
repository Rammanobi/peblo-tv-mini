import io

import pytest
from PIL import Image

pytestmark = pytest.mark.asyncio


def _png_bytes(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(1, 2, 3)).save(buf, format="PNG")
    return buf.getvalue()


async def _new_show(client, headers):
    r = await client.post("/shows", headers=headers, json={"title": "AW Show", "category": "comedy"})
    return r.json()


async def test_wrong_aspect_ratio_rejected(client, editor_token):
    headers = {"Authorization": f"Bearer {editor_token}"}
    show = await _new_show(client, headers)
    files = {"file": ("poster.png", _png_bytes(800, 900), "image/png")}
    r = await client.post(f"/shows/{show['id']}/artwork", headers=headers, data={"kind": "poster"}, files=files)
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["details"][0]["code"] == "ARTWORK_ASPECT_RATIO"


async def test_oversized_file_rejected(client, editor_token):
    headers = {"Authorization": f"Bearer {editor_token}"}
    show = await _new_show(client, headers)
    big = b"\xff" * (205000)
    # Wrap in a valid-looking png header won't matter; size check happens before decode.
    files = {"file": ("banner.png", big, "image/png")}
    r = await client.post(f"/shows/{show['id']}/artwork", headers=headers, data={"kind": "banner"}, files=files)
    assert r.status_code == 413
    body = r.json()
    assert body["error"]["type"] == "payload_too_large"
    assert body["error"]["details"][0]["code"] == "ARTWORK_SIZE_LIMIT"


async def test_wrong_mime_type_rejected(client, editor_token):
    headers = {"Authorization": f"Bearer {editor_token}"}
    show = await _new_show(client, headers)
    files = {"file": ("poster.gif", b"GIF89a" + b"0" * 100, "image/gif")}
    r = await client.post(f"/shows/{show['id']}/artwork", headers=headers, data={"kind": "poster"}, files=files)
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["code"] == "ARTWORK_MIME_TYPE"


async def test_valid_poster_accepted(client, editor_token):
    headers = {"Authorization": f"Bearer {editor_token}"}
    show = await _new_show(client, headers)
    files = {"file": ("poster.png", _png_bytes(600, 900), "image/png")}
    r = await client.post(f"/shows/{show['id']}/artwork", headers=headers, data={"kind": "poster"}, files=files)
    assert r.status_code == 201
    body = r.json()
    assert body["width"] == 600 and body["height"] == 900
