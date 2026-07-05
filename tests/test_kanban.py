"""Kanban lifecycle: create → update → comment → link → block → complete."""


def make_task(client, title="Test task", **kw):
    payload = {"title": title, "body": "body", "status": "triage", "priority": "medium", "assignee": "", **kw}
    r = client.post("/api/kanban/tasks", json=payload)
    assert r.status_code == 200
    return r.json()


def test_create_and_board(client):
    t = make_task(client, title="Board me")
    board = client.get("/api/kanban/board").json()
    ids = [x["id"] for x in board["columns"]["triage"]]
    assert t["id"] in ids


def test_get_update_task(client):
    t = make_task(client)
    r = client.patch(f"/api/kanban/tasks/{t['id']}", json={"status": "todo", "priority": "high"})
    assert r.status_code == 200
    got = client.get(f"/api/kanban/tasks/{t['id']}").json()
    assert got["status"] == "todo"
    assert got["priority"] == "high"


def test_missing_task_404(client):
    assert client.get("/api/kanban/tasks/zzzzzzzz").status_code == 404


def test_comment_and_links(client):
    a = make_task(client, title="parent")
    b = make_task(client, title="child")
    r = client.post(f"/api/kanban/tasks/{a['id']}/comments", json={"message": "note"})
    assert r.status_code == 200
    r = client.post("/api/kanban/links", json={"parent_id": a["id"], "child_id": b["id"]})
    assert r.status_code == 200


def test_block_unblock_complete(client):
    t = make_task(client)
    r = client.post(f"/api/kanban/tasks/{t['id']}/block", json={"reason": "waiting"})
    assert r.status_code == 200
    assert client.get(f"/api/kanban/tasks/{t['id']}").json()["status"] == "blocked"

    r = client.post(f"/api/kanban/tasks/{t['id']}/unblock")
    assert client.get(f"/api/kanban/tasks/{t['id']}").json()["status"] == "ready"

    r = client.post(f"/api/kanban/tasks/{t['id']}/complete", json={"summary": "done"})
    assert client.get(f"/api/kanban/tasks/{t['id']}").json()["status"] == "done"
