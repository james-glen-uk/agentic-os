"""Scheduler job CRUD, manual trigger, events history, webhooks."""


def test_default_jobs_present(client):
    jobs = client.get("/api/scheduler/jobs").json()
    names = {j["name"] for j in jobs}
    assert {"Heartbeat Check", "Daily Standup"} <= names


def test_job_create_list_delete(client):
    r = client.post("/api/scheduler/jobs", json={
        "name": "Test Job", "skill": "heartbeat", "cron": "0 12 * * *", "enabled": True,
    })
    assert r.status_code == 200
    job = r.json()
    assert job["id"]

    names = {j["name"] for j in client.get("/api/scheduler/jobs").json()}
    assert "Test Job" in names

    assert client.delete(f"/api/scheduler/jobs/{job['id']}").json()["status"] == "deleted"
    names = {j["name"] for j in client.get("/api/scheduler/jobs").json()}
    assert "Test Job" not in names


def test_delete_unknown_job_404(client):
    assert client.delete("/api/scheduler/jobs/zzzzzzzz").status_code == 404


def test_manual_trigger(client):
    jobs = client.get("/api/scheduler/jobs").json()
    job_id = next(j["id"] for j in jobs if j["name"] == "Heartbeat Check")
    r = client.post(f"/api/scheduler/trigger/{job_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "triggered"


def test_events_history_records_runs(client):
    events = client.get("/api/scheduler/events").json()["events"]
    assert any(e.get("skill") == "heartbeat" for e in events)


def test_webhook_triggers_skill(client):
    r = client.post("/api/webhook", json={"event": "test", "skill": "heartbeat", "payload": {"a": 1}})
    assert r.status_code == 200
    assert r.json()["status"] == "processed"


def test_webhook_without_skill_is_received(client):
    r = client.post("/api/webhook", json={"event": "noop"})
    assert r.json()["status"] == "received"
