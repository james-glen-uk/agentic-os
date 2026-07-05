"""Hey Jarvis voice: service state machine, command parsing, and execution."""
import json

import pytest


# ─── voice_service (no mic; deps optional) ────────────────────────

def test_voice_service_reports_unavailable_without_deps(server):
    import voice_service
    svc = voice_service.VoiceService()
    status = svc.status()
    # The heavy audio deps aren't installed in the test env
    assert status["missing"]
    assert status["available"] is False
    assert "requirements-voice.txt" in status["install_hint"]


def test_enable_degrades_when_deps_missing(client):
    r = client.post("/api/voice/enable")
    body = r.json()
    assert body["state"] in ("unavailable", "idle")
    if not body["available"]:
        assert body["state"] == "unavailable"


def test_feed_transcript_invokes_handler(server):
    import voice_service
    seen = {}
    def handler(t):
        seen["t"] = t
        return {"status": "ok"}
    svc = voice_service.VoiceService(on_transcript=handler)
    out = svc.feed_transcript("hello world")
    assert seen["t"] == "hello world"
    assert out == {"status": "ok"}
    assert svc.last_transcript == "hello world"


def test_feed_transcript_survives_handler_error(server):
    import voice_service
    def boom(_):
        raise RuntimeError("nope")
    svc = voice_service.VoiceService(on_transcript=boom)
    out = svc.feed_transcript("x")
    assert out["status"] == "error"  # never propagates


# ─── command parsing (LLM mocked) ─────────────────────────────────

@pytest.fixture()
def parse_as(server, monkeypatch):
    """Make the LLM 'parse' return a given action dict."""
    def _set(action):
        monkeypatch.setattr(server, "execute_agent", lambda a, m: json.dumps(action))
    return _set


def test_parse_navigate(client, server, parse_as):
    parse_as({"action": "navigate", "params": {"page": "journal"}, "label": "Open journal"})
    r = client.post("/api/voice/command", json={"transcript": "go to my journal", "execute": False})
    body = r.json()
    assert body["status"] == "pending_confirm"
    assert body["action"] == "navigate"
    assert body["params"]["page"] == "journal"


def test_unrecognized_command(client, server, parse_as):
    parse_as({"action": "none", "params": {}, "label": ""})
    r = client.post("/api/voice/command", json={"transcript": "sing me a song"})
    assert r.json()["status"] == "unrecognized"


def test_execute_create_schedule(client, server, parse_as):
    parse_as({"action": "create_schedule",
              "params": {"name": "Morning Brief", "skill": "daily-standup", "cron": "0 8 * * *"},
              "label": "Schedule Morning Brief"})
    r = client.post("/api/voice/command", json={"transcript": "schedule a daily standup at 8am", "execute": True})
    body = r.json()
    assert body["status"] == "executed"
    assert body["result"]["status"] == "ok"
    names = {j["name"] for j in client.get("/api/scheduler/jobs").json()}
    assert "Morning Brief" in names


def test_execute_add_journal(client, server, parse_as):
    parse_as({"action": "add_journal", "params": {"text": "Shipped the voice assistant"}, "label": "Journal"})
    r = client.post("/api/voice/command", json={"transcript": "add a journal note that I shipped voice", "execute": True})
    assert r.json()["result"]["status"] == "ok"
    date = r.json()["result"]["date"]
    entry = client.get(f"/api/journal/entries/{date}").json()["content"]
    assert "Shipped the voice assistant" in entry


def test_execute_create_goal_and_task(client, server, parse_as):
    parse_as({"action": "create_goal", "params": {"title": "Launch v2"}, "label": "Goal"})
    r = client.post("/api/voice/command", json={"transcript": "create a goal to launch v2", "execute": True})
    assert r.json()["result"]["status"] == "ok"
    assert any(g["title"] == "Launch v2" for g in client.get("/api/goals").json()["goals"])

    parse_as({"action": "create_task", "params": {"title": "Write release notes"}, "label": "Task"})
    r = client.post("/api/voice/command", json={"transcript": "add a task to write release notes", "execute": True})
    assert r.json()["result"]["status"] == "ok"


def test_execute_via_confirm_flow(client, server, parse_as):
    parse_as({"action": "create_goal", "params": {"title": "Confirmed goal"}, "label": "Goal"})
    pending = client.post("/api/voice/command", json={"transcript": "make a goal", "execute": False}).json()
    assert pending["status"] == "pending_confirm"
    done = client.post("/api/voice/execute", json={"action": pending["action"], "params": pending["params"]}).json()
    assert done["status"] == "ok"
    assert any(g["title"] == "Confirmed goal" for g in client.get("/api/goals").json()["goals"])


def test_empty_transcript_rejected(client):
    assert client.post("/api/voice/command", json={"transcript": "  "}).status_code == 400


def test_execute_unknown_action_rejected(client):
    assert client.post("/api/voice/execute", json={"action": "launch_missiles"}).status_code == 400


def test_no_agent_reports_clearly(client, server, monkeypatch):
    # Every agent "fails" → parse can't run → distinct status, not "unrecognized"
    monkeypatch.setattr(server, "execute_agent", lambda a, m: "⚠ Agent CLI not installed.")
    r = client.post("/api/voice/command", json={"transcript": "do something", "execute": True})
    assert r.json()["status"] == "no_agent"


def test_run_skill_action(client, server, monkeypatch):
    monkeypatch.setattr(server, "execute_agent",
                        lambda a, m: json.dumps({"action": "run_skill", "params": {"skill": "heartbeat"}, "label": "Run"})
                        if "convert a spoken command" in m else "skill output")
    r = client.post("/api/voice/command", json={"transcript": "run the heartbeat skill", "execute": True})
    assert r.json()["result"]["status"] == "ok"
    assert r.json()["result"]["skill"] == "heartbeat"
