"""Goals CRUD (+ brain sync) and journal entries/search."""


def test_goal_lifecycle_and_brain_sync(client, server):
    r = client.post("/api/goals", json={
        "title": "Ship Phase 0", "description": "Hardening epic", "category": "eng", "target_date": "2026-08-01",
    })
    assert r.status_code == 200
    goal = r.json()
    assert goal["status"] == "active" and goal["progress"] == 0

    # Auto-synced into brain/active-projects.md
    active = (server.BASE_DIR / "brain" / "active-projects.md").read_text(encoding="utf-8")
    assert "Ship Phase 0" in active

    r = client.put(f"/api/goals/{goal['id']}", json={"progress": 50})
    assert r.json()["progress"] == 50

    assert client.delete(f"/api/goals/{goal['id']}").status_code == 200
    ids = [g["id"] for g in client.get("/api/goals").json()["goals"]]
    assert goal["id"] not in ids


def test_update_missing_goal_404(client):
    assert client.put("/api/goals/zzzzzzzz", json={"progress": 10}).status_code == 404


def test_journal_write_read_search(client):
    date = "2026-07-03"
    r = client.put(f"/api/journal/entries/{date}", json={"content": "# Today\n\nFixed the zebraphrase bug.\n"})
    assert r.status_code == 200

    r = client.get(f"/api/journal/entries/{date}")
    assert "zebraphrase" in r.json()["content"]

    dates = [e["date"] if isinstance(e, dict) else e for e in client.get("/api/journal/entries").json()["entries"]]
    assert any(date in str(d) for d in dates)

    r = client.get("/api/journal/search", params={"q": "zebraphrase"})
    assert r.status_code == 200
    assert len(r.json()["results"]) >= 1
