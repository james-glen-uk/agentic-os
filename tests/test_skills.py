"""Skills endpoints: listing, detail, run (agent mocked), auto-routing."""
import pytest


@pytest.fixture()
def fake_agent(server, monkeypatch):
    calls = []

    def fake_execute(agent, message):
        calls.append({"agent": agent, "message": message})
        return f"[mock:{agent}] done"

    monkeypatch.setattr(server, "execute_agent", fake_execute)
    return calls


def test_list_skills(client):
    r = client.get("/api/skills")
    assert r.status_code == 200
    names = {s["name"] for s in r.json()}
    assert {"heartbeat", "devops-audit", "content-draft"} <= names
    assert not any(n.startswith("_") for n in names)


def test_skills_count_counts_directories(client):
    # Regression: /api/status counted files in skills/, but skills are dirs
    listed = len(client.get("/api/skills").json())
    counted = client.get("/api/status").json()["skills_count"]
    assert counted == listed > 0


def test_skill_detail(client):
    r = client.get("/api/skills/heartbeat")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "heartbeat"
    assert "skill" in body and "eval" in body


def test_skill_404_and_traversal(client):
    assert client.get("/api/skills/does-not-exist").status_code == 404
    assert client.get("/api/skills/..evil").status_code == 400
    assert client.post("/api/skills/..evil/run").status_code == 400


def test_run_skill_mocked(client, server, fake_agent):
    r = client.post("/api/skills/heartbeat/run", json={"input": "ping", "agent": "opencode"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["agent"] == "opencode"
    assert body["output"] == "[mock:opencode] done"
    # Run is recorded in learnings.md
    learnings = (server.BASE_DIR / "skills" / "heartbeat" / "learnings.md").read_text(encoding="utf-8")
    assert "[mock:opencode] done" in learnings


def test_auto_routing_by_skill_name(client, fake_agent):
    r = client.post("/api/skills/devops-audit/run", json={"input": "", "agent": "auto"})
    assert r.json()["agent"] == "opencode"
    r = client.post("/api/skills/research-synthesis/run", json={"input": "", "agent": "auto"})
    assert r.json()["agent"] == "gemini"
