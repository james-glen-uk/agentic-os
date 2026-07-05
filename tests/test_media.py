"""Image generation: graceful unconfigured state, mocked provider, preview."""
import pytest


def test_image_unconfigured_is_graceful(client):
    # No media.image_provider set → clear setup message, not a 500
    r = client.post("/api/media/image", json={"prompt": "a red fox"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unconfigured"
    assert "provider" in body["message"].lower()


def test_empty_prompt_rejected(client):
    assert client.post("/api/media/image", json={"prompt": "  "}).status_code == 400


def test_presets_endpoint(client):
    body = client.get("/api/media/presets").json()
    assert "photo" in body["presets"]
    assert body["configured"] is False


@pytest.fixture()
def fake_image_provider(server, monkeypatch):
    png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)  # minimal PNG-ish bytes

    def fake(prompt, preset=""):
        return {"ok": True, "data": png, "mime": "image/png", "ext": "png"}

    monkeypatch.setattr(server, "generate_image", fake)
    return png


def test_image_generation_creates_image_artifact(client, server, fake_image_provider):
    r = client.post("/api/media/image", json={"prompt": "a blue cat", "preset": "photo"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    art_id = body["artifact_id"]

    art = client.get(f"/api/artifacts/{art_id}").json()
    assert art["type"] == "image"
    assert art["content"] == ""  # binary not inlined
    assert art["raw_url"].endswith("/raw")

    raw = client.get(f"/api/artifacts/{art_id}/raw")
    assert raw.status_code == 200
    assert raw.headers["content-type"] == "image/png"
    assert raw.content == fake_image_provider


def test_image_artifact_shows_in_library(client, server, fake_image_provider):
    art_id = client.post("/api/media/image", json={"prompt": "a green dog"}).json()["artifact_id"]
    listed = client.get("/api/artifacts", params={"skill": "image-gen"}).json()["artifacts"]
    assert any(a["id"] == art_id and a["type"] == "image" for a in listed)
