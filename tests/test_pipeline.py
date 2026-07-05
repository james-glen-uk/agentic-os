"""Idea → Spec → Build → Preview pipeline (sandboxed builds)."""
import time

import pytest


def _make_idea(client, title="Build a hello page", body="A single index.html that says hello"):
    r = client.post("/api/kanban/tasks", json={
        "title": title, "body": body, "status": "triage",
        "priority": "medium", "assignee": "",
    })
    assert r.status_code == 200
    return r.json()["id"]


def _wait_build(client, task_id, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        t = client.get(f"/api/kanban/tasks/{task_id}").json()
        if t.get("build_status") in ("completed", "failed"):
            return t
        time.sleep(0.1)
    return client.get(f"/api/kanban/tasks/{task_id}").json()


def test_specify_drafts_spec_and_advances(client, server, monkeypatch):
    monkeypatch.setattr(server, "execute_agent", lambda a, m: "SPEC: create index.html with an h1")
    tid = _make_idea(client)
    r = client.post(f"/api/kanban/tasks/{tid}/specify")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "todo"
    assert "SPEC:" in body["spec"]


@pytest.fixture()
def fake_build(server, monkeypatch):
    """Simulate a Claude build: write a real file into the sandbox."""
    def fake(sandbox, prompt):
        (sandbox / "index.html").write_text("<h1>hello</h1>", encoding="utf-8")
        return {"ok": True, "output": "Created index.html", "cost": 0.05}
    monkeypatch.setattr(server, "_run_build_agent", fake)


def test_build_runs_in_sandbox_and_produces_files(client, server, fake_build):
    tid = _make_idea(client)
    r = client.post(f"/api/kanban/tasks/{tid}/build")
    assert r.status_code == 200
    assert r.json()["build_status"] == "running"

    t = _wait_build(client, tid)
    assert t["build_status"] == "completed"
    assert t["status"] == "done"
    assert any(f["path"] == "index.html" for f in t["build_files"])
    # File actually lives under the per-task sandbox
    assert (server.WORKSPACE_DIR / tid / "index.html").is_file()


def test_preview_lists_and_reads_files(client, server, fake_build):
    tid = _make_idea(client)
    client.post(f"/api/kanban/tasks/{tid}/build")
    _wait_build(client, tid)

    listing = client.get(f"/api/kanban/tasks/{tid}/preview").json()
    assert any(f["path"] == "index.html" for f in listing["files"])

    content = client.get(f"/api/kanban/tasks/{tid}/preview", params={"file": "index.html"}).json()
    assert content["content"] == "<h1>hello</h1>"


def test_preview_rejects_sandbox_escape(client, server, fake_build):
    tid = _make_idea(client)
    client.post(f"/api/kanban/tasks/{tid}/build")
    _wait_build(client, tid)
    # Traversal outside the sandbox is rejected
    for bad in ["../../server.py", "..%2f..%2fserver.py", "/etc/passwd"]:
        r = client.get(f"/api/kanban/tasks/{tid}/preview", params={"file": bad})
        assert r.status_code in (400, 404)


def test_build_failure_blocks_task(client, server, monkeypatch):
    monkeypatch.setattr(server, "_run_build_agent",
                        lambda sandbox, prompt: {"ok": False, "output": "boom", "cost": 0})
    tid = _make_idea(client)
    client.post(f"/api/kanban/tasks/{tid}/build")
    t = _wait_build(client, tid)
    assert t["build_status"] == "failed"
    assert t["status"] == "blocked"


def test_invalid_task_id_rejected(client):
    assert client.get("/api/kanban/tasks/..%2f..%2fetc/preview").status_code in (400, 404)
    assert client.post("/api/kanban/tasks/zzzzzzzz/build").status_code == 404
