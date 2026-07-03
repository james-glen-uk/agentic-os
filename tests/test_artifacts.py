"""Artifact library: auto-save from skill runs, CRUD, filters, FTS."""
import pytest


@pytest.fixture()
def fake_agent(server, monkeypatch):
    monkeypatch.setattr(server, "execute_agent",
                        lambda a, m: "# Draft\n\nThe migratory wombat report is ready.")


def run_skill(client, **kw):
    payload = {"input": "", "agent": "opencode", **kw}
    r = client.post("/api/skills/content-draft/run", json=payload)
    assert r.status_code == 200
    return r.json()


def test_skill_run_saves_artifact(client, fake_agent):
    body = run_skill(client)
    assert body["artifact_id"]
    art = client.get(f"/api/artifacts/{body['artifact_id']}").json()
    assert art["skill"] == "content-draft"
    assert art["agent"] == "opencode"
    assert "migratory wombat" in art["content"]
    assert art["size"] > 0


def test_topic_recorded_on_artifact(client, fake_agent):
    body = run_skill(client, topic="AI agents trend")
    art = client.get(f"/api/artifacts/{body['artifact_id']}").json()
    assert art["source_topic"] == "AI agents trend"
    assert "AI agents trend" in art["title"]


def test_list_filter_and_search(client, fake_agent):
    body = run_skill(client)
    listed = client.get("/api/artifacts").json()["artifacts"]
    assert any(a["id"] == body["artifact_id"] for a in listed)
    assert all("preview" in a for a in listed)

    by_skill = client.get("/api/artifacts", params={"skill": "content-draft"}).json()["artifacts"]
    assert any(a["id"] == body["artifact_id"] for a in by_skill)
    assert client.get("/api/artifacts", params={"skill": "nope"}).json()["artifacts"] == []

    by_q = client.get("/api/artifacts", params={"q": "wombat"}).json()["artifacts"]
    assert any(a["id"] == body["artifact_id"] for a in by_q)


def test_bookmark_and_tags(client, fake_agent):
    art_id = run_skill(client)["artifact_id"]
    r = client.patch(f"/api/artifacts/{art_id}", json={"bookmarked": True, "tags": ["seo", "draft"]})
    assert r.json()["bookmarked"] is True

    marked = client.get("/api/artifacts", params={"bookmarked": True}).json()["artifacts"]
    assert any(a["id"] == art_id for a in marked)
    by_tag = client.get("/api/artifacts", params={"tag": "seo"}).json()["artifacts"]
    assert any(a["id"] == art_id for a in by_tag)


def test_delete_artifact(client, fake_agent, server):
    art_id = run_skill(client)["artifact_id"]
    meta = client.get(f"/api/artifacts/{art_id}").json()
    assert client.delete(f"/api/artifacts/{art_id}").json()["status"] == "deleted"
    assert client.get(f"/api/artifacts/{art_id}").status_code == 404
    assert not (server.ARTIFACTS_DIR / meta["content_file"]).exists()


def test_invalid_ids_rejected(client):
    assert client.get("/api/artifacts/..evil").status_code == 400
    assert client.get("/api/artifacts/zzzzzzzz").status_code == 400  # non-hex
    assert client.get("/api/artifacts/abcd1234").status_code == 404  # valid shape, missing


def test_artifacts_surface_in_memory_search(client, fake_agent):
    run_skill(client)
    client.post("/api/memory/reindex")
    results = client.get("/api/memory/search", params={"q": "wombat"}).json()["results"]
    assert any(r.get("category") == "artifact" or "artifact" in str(r) for r in results)


def test_failed_run_saves_no_artifact(client, server, monkeypatch):
    monkeypatch.setattr(server, "execute_agent", lambda a, m: "⚠ Agent CLI not installed.")
    before = client.get("/api/artifacts", params={"limit": 200}).json()["total"]
    r = client.post("/api/skills/content-draft/run", json={"input": "", "agent": "auto"})
    assert r.json()["status"] == "failed"
    assert r.json()["artifact_id"] is None
    after = client.get("/api/artifacts", params={"limit": 200}).json()["total"]
    assert after == before
