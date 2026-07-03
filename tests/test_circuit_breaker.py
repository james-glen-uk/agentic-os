"""Circuit breaker trip/open/reset and error-log endpoints."""


def test_trip_opens_after_threshold(client):
    client.post("/api/circuit-breaker/reset", json={"agent": "opencode"})
    state = client.get("/api/circuit-breaker").json()
    threshold = state.get("threshold", 3)

    for i in range(threshold):
        r = client.post("/api/circuit-breaker/trip", json={"agent": "opencode"})
        assert r.status_code == 200
    assert r.json()["state"] == "open"

    r = client.post("/api/circuit-breaker/reset", json={"agent": "opencode"})
    assert r.json()["state"] == "closed"


def test_invalid_agent_rejected(client):
    assert client.post("/api/circuit-breaker/trip", json={"agent": "evil"}).status_code == 400
    assert client.post("/api/circuit-breaker/reset", json={"agent": ""}).status_code == 400


def test_error_log_report_get_clear(client):
    r = client.post("/api/errors/report", json={"source": "test", "message": "boom", "category": "system"})
    assert r.status_code == 200

    errors = client.get("/api/errors").json()["errors"]
    assert any(e.get("message") == "boom" for e in errors)

    by_cat = client.get("/api/errors", params={"category": "system"}).json()["errors"]
    assert all(e.get("category") == "system" for e in by_cat)

    client.delete("/api/errors")
    assert client.get("/api/errors").json()["errors"] == []
