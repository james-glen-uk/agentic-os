"""Multi-agent orchestration: decomposition, subtasks, aggregation, caps."""
import json
import time

import pytest


def _wait_for_status(client, run_id, statuses, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/orchestrate/{run_id}").json()
        if run["status"] in statuses:
            return run
        time.sleep(0.1)
    return client.get(f"/api/orchestrate/{run_id}").json()


@pytest.fixture()
def fake_orchestrator(server, monkeypatch):
    """CEO decomposition returns 3 roles; every other call returns text."""
    calls = []

    def fake(agent, message):
        calls.append({"agent": agent, "message": message})
        if "JSON array" in message:
            return json.dumps([
                {"role": "researcher", "title": "Research the topic", "description": "gather facts"},
                {"role": "builder", "title": "Build the deliverable", "description": "make it"},
                {"role": "reviewer", "title": "Review the result", "description": "check it"},
            ])
        return f"[{agent}] output for {message[:30]}"

    monkeypatch.setattr(server, "execute_agent", fake)
    return calls


def test_roles_endpoint(client):
    roles = client.get("/api/roles").json()["roles"]
    names = {r["name"] for r in roles}
    assert {"ceo", "cto", "researcher", "builder", "reviewer"} == names
    assert all(r["primary"] in ["opencode", "hermes", "gemini", "claude"] for r in roles)


def test_orchestration_full_run(client, server, fake_orchestrator):
    r = client.post("/api/orchestrate", json={"goal": "Write a launch plan"})
    assert r.status_code == 200
    run_id = r.json()["id"]
    assert r.json()["status"] == "planning"

    run = _wait_for_status(client, run_id, {"completed", "failed"})
    assert run["status"] == "completed"
    assert len(run["subtasks"]) == 3
    assert [s["role"] for s in run["subtasks"]] == ["researcher", "builder", "reviewer"]
    assert all(s["status"] == "done" for s in run["subtasks"])
    assert all(s["artifact_id"] for s in run["subtasks"])
    assert run["artifact_id"]  # final aggregated artifact


def test_subtasks_become_linked_kanban_tasks(client, server, fake_orchestrator):
    run_id = client.post("/api/orchestrate", json={"goal": "Ship a feature"}).json()["id"]
    run = _wait_for_status(client, run_id, {"completed", "failed"})

    parent = client.get(f"/api/kanban/tasks/{run['parent_task_id']}").json()
    child_ids = {l["child"] for l in parent["links"]}
    assert child_ids == {s["kanban_id"] for s in run["subtasks"]}
    for st in run["subtasks"]:
        child = client.get(f"/api/kanban/tasks/{st['kanban_id']}").json()
        assert child["assignee"] == st["role"]
        assert child["status"] == "done"


def test_aggregated_artifact_has_content(client, server, fake_orchestrator):
    run_id = client.post("/api/orchestrate", json={"goal": "Summarize AI news"}).json()["id"]
    run = _wait_for_status(client, run_id, {"completed", "failed"})
    art = client.get(f"/api/artifacts/{run['artifact_id']}").json()
    assert art["skill"] == "orchestrate:ceo"
    assert art["content"]


def test_max_subtasks_cap(client, server, fake_orchestrator):
    run_id = client.post("/api/orchestrate", json={"goal": "Do a thing", "max_subtasks": 2}).json()["id"]
    run = _wait_for_status(client, run_id, {"completed", "failed"})
    assert len(run["subtasks"]) == 2


def test_max_agent_calls_cap_skips_later_subtasks(client, server, fake_orchestrator):
    client.put("/api/settings", json={"settings": {"orchestration": {"max_agent_calls": 2}}})
    try:
        run_id = client.post("/api/orchestrate", json={"goal": "Big goal"}).json()["id"]
        run = _wait_for_status(client, run_id, {"completed", "failed"})
        # 1 call for planning; only 1 subtask can run before the cap; rest skipped
        skipped = [s for s in run["subtasks"] if s["status"] == "skipped"]
        assert skipped
    finally:
        client.put("/api/settings", json={"settings": {"orchestration": {}}})


def test_degrades_when_plan_unparseable(client, server, monkeypatch):
    monkeypatch.setattr(server, "execute_agent", lambda a, m: "not json at all")
    run_id = client.post("/api/orchestrate", json={"goal": "Fallback goal"}).json()["id"]
    run = _wait_for_status(client, run_id, {"completed", "failed"})
    # One degraded builder subtask
    assert len(run["subtasks"]) == 1
    assert run["subtasks"][0]["role"] == "builder"


def test_empty_goal_rejected(client):
    assert client.post("/api/orchestrate", json={"goal": "   "}).status_code == 400


def test_invalid_run_id(client):
    assert client.get("/api/orchestrate/../etc").status_code in (400, 404)
    assert client.get("/api/orchestrate/zzzzzzzz").status_code == 400  # non-hex
    assert client.get("/api/orchestrate/abcd1234").status_code == 404
