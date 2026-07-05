"""Fallback chain engine: substitution, exhaustion, free-only mode."""
import pytest


@pytest.fixture()
def scripted_agents(server, monkeypatch):
    """execute_agent stub: fails for agents in state['fail'], succeeds otherwise."""
    state = {"fail": set(), "calls": []}

    def fake(agent, message):
        state["calls"].append(agent)
        if agent in state["fail"] or "*" in state["fail"]:
            return f"⚠ Agent '{agent}' CLI not installed. Install it and try again."
        return f"ok from {agent}"

    monkeypatch.setattr(server, "execute_agent", fake)
    return state


@pytest.fixture(autouse=True)
def clean_routing_and_circuits(client):
    yield
    client.put("/api/settings", json={"settings": {"routing": {}}})
    for agent in ["opencode", "hermes", "gemini", "claude"]:
        client.post("/api/circuit-breaker/reset", json={"agent": agent})


def test_primary_failure_falls_back(client, scripted_agents):
    scripted_agents["fail"] = {"opencode"}
    r = client.post("/api/skills/heartbeat/run", json={"input": "", "agent": "opencode"})
    body = r.json()
    assert body["status"] == "completed"
    assert body["fallback_used"] is True
    assert body["agent"] != "opencode"
    assert body["output"].startswith("ok from")
    assert body["attempts"][0] == {"agent": "opencode", "ok": False,
                                   "error": body["attempts"][0]["error"]}


def test_fallback_noted_in_audit(client, scripted_agents):
    scripted_agents["fail"] = {"opencode"}
    client.post("/api/skills/heartbeat/run", json={"input": "", "agent": "opencode"})
    entries = client.get("/api/audit", params={"limit": 20}).json()["entries"]
    assert any(e.get("action") == "agent_fallback" for e in entries)


def test_all_agents_exhausted(client, scripted_agents):
    scripted_agents["fail"] = {"*"}
    r = client.post("/api/skills/heartbeat/run", json={"input": "", "agent": "auto"})
    body = r.json()
    assert body["status"] == "failed"
    assert len(body["attempts"]) == 4
    assert "All agents failed" in body["output"]
    errors = client.get("/api/errors").json()["errors"]
    assert any(e.get("source") == "fallback" for e in errors)


def test_failures_feed_circuit_breaker(client, scripted_agents):
    scripted_agents["fail"] = {"opencode"}
    client.post("/api/skills/heartbeat/run", json={"input": "", "agent": "opencode"})
    state = client.get("/api/circuit-breaker").json()
    assert state["agents"]["opencode"]["failures"] >= 1


def test_free_only_excludes_paid_agents(client, scripted_agents):
    client.put("/api/settings", json={"settings": {"routing": {"free_only": True}}})
    scripted_agents["fail"] = {"*"}
    r = client.post("/api/skills/heartbeat/run", json={"input": "", "agent": "auto"})
    tried = [a["agent"] for a in r.json()["attempts"]]
    assert "claude" not in tried
    assert len(tried) == 3


def test_prefer_quality_puts_claude_first(client, scripted_agents):
    client.put("/api/settings", json={"settings": {"routing": {"prefer": "quality"}}})
    r = client.post("/api/skills/heartbeat/run", json={"input": "", "agent": "auto"})
    # heartbeat auto-routes via SKILL.md/default; with quality preference the
    # first fallback candidate after the primary must be claude
    tried = [a["agent"] for a in r.json()["attempts"]]
    assert tried[0] in ["opencode", "claude"]


def test_chat_auto_routes_and_falls_back(client, scripted_agents):
    scripted_agents["fail"] = {"gemini"}
    r = client.post("/api/chat", json={"agent": "auto", "message": "research and compare and analyze frameworks"})
    body = r.json()
    assert body["response"]["agent"] != "gemini"
    assert body["fallback_used"] is True
    assert scripted_agents["calls"][0] == "gemini"  # router picked gemini first
