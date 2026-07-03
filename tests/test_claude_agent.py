"""Claude Code as fourth agent: chat path, JSON parsing, cost, failures."""
import json
import subprocess

import pytest


def claude_json(result="Hello from Claude", cost=0.0123):
    return json.dumps({
        "type": "result", "subtype": "success", "result": result,
        "total_cost_usd": cost,
        "usage": {"input_tokens": 100, "output_tokens": 50},
    })


@pytest.fixture()
def fake_run_cli(server, monkeypatch):
    """Patch run_cli; returns a dict you can configure per-test."""
    state = {"code": 0, "out": claude_json(), "err": "", "raise_timeout": False, "calls": []}

    def fake(args, timeout=30):
        state["calls"].append({"args": args, "timeout": timeout})
        if state["raise_timeout"]:
            raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)
        return state["code"], state["out"], state["err"]

    monkeypatch.setattr(server, "run_cli", fake)
    return state


def test_chat_accepts_claude(client, fake_run_cli):
    r = client.post("/api/chat", json={"agent": "claude", "message": "hi"})
    assert r.status_code == 200
    assert r.json()["response"]["content"] == "Hello from Claude"
    # Headless invocation shape
    args = fake_run_cli["calls"][0]["args"]
    assert args[0] == "claude" and "-p" in args and "--output-format" in args


def test_claude_cost_recorded(client, server, fake_run_cli):
    client.post("/api/chat", json={"agent": "claude", "message": "hi"})
    cost = json.loads((server.BASE_DIR / "data" / "cost-history.json").read_text(encoding="utf-8"))
    claude_entries = [e for e in cost["entries"] if e["agent"] == "claude"]
    assert claude_entries and claude_entries[-1]["cost"] == pytest.approx(0.0123)
    assert claude_entries[-1]["tokens"] == 150


def test_claude_timeout_is_graceful(client, fake_run_cli):
    fake_run_cli["raise_timeout"] = True
    r = client.post("/api/chat", json={"agent": "claude", "message": "hi"})
    assert r.status_code == 200
    assert "timed out" in r.json()["response"]["content"]


def test_claude_auth_error_hint(client, fake_run_cli):
    fake_run_cli.update({"code": 1, "out": "", "err": "Please log in with `claude login`"})
    r = client.post("/api/chat", json={"agent": "claude", "message": "hi"})
    # Auth failure triggers fallback; the hint is preserved in the attempt log
    attempts = r.json()["attempts"]
    assert attempts[0]["agent"] == "claude"
    assert "needs auth" in attempts[0]["error"]


def test_claude_non_json_output_falls_back(client, fake_run_cli):
    fake_run_cli["out"] = "plain text answer"
    r = client.post("/api/chat", json={"agent": "claude", "message": "hi"})
    assert r.json()["response"]["content"] == "plain text answer"


def test_unknown_agent_still_rejected(client):
    assert client.post("/api/chat", json={"agent": "evil", "message": "hi"}).status_code == 400


def test_claude_in_status_and_health(client):
    names = {a["name"] for a in client.get("/api/status").json()["agents"]}
    assert "claude" in names
    names = {a["name"] for a in client.get("/api/agents/health").json()["agents"]}
    assert "claude" in names


def test_circuit_breaker_accepts_claude(client):
    r = client.post("/api/circuit-breaker/trip", json={"agent": "claude"})
    assert r.status_code == 200
    r = client.post("/api/circuit-breaker/reset", json={"agent": "claude"})
    assert r.json()["state"] == "closed"


def test_router_suggests_claude_for_complex_builds(client):
    r = client.post("/api/router/suggest", json={"task": "implement a multi-step feature and refactor the architecture"})
    assert r.json()["suggested_agent"] == "claude"


def test_skill_primary_claude_honored(client, server, monkeypatch):
    calls = []
    monkeypatch.setattr(server, "execute_agent", lambda a, m: calls.append(a) or "ok")
    skill_dir = server.BASE_DIR / "skills" / "claude-test-skill"
    skill_dir.mkdir(exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# Test\n\nPrimary: claude\n", encoding="utf-8")
    r = client.post("/api/skills/claude-test-skill/run", json={"input": "", "agent": "auto"})
    assert r.json()["agent"] == "claude"
    assert calls == ["claude"]
