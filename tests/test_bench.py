"""Backend benchmark: scoring, leaderboard, and quality-routing feed."""
import pytest


@pytest.fixture()
def scored_agents(server, monkeypatch):
    """claude answers correctly; opencode gets everything wrong."""
    answers = {"391": "391", "paris": "Paris", "[::-1]": "s[::-1]"}

    def fake(agent, prompt):
        if agent == "claude":
            for key, val in answers.items():
                if key == "391" and "17 times 23" in prompt:
                    return "391"
                if key == "paris" and "capital of France" in prompt:
                    return "Paris"
                if "reverses a string" in prompt:
                    return "s[::-1]"
            return "?"
        return "no idea"  # opencode: all wrong

    monkeypatch.setattr(server, "execute_agent", fake)


def test_bench_tasks_endpoint(client):
    tasks = client.get("/api/bench/tasks").json()["tasks"]
    ids = {t["id"] for t in tasks}
    assert {"arithmetic", "capital", "code"} <= ids


def test_bench_run_scores_and_ranks(client, server, scored_agents):
    r = client.post("/api/bench/run", json={"agents": ["opencode", "claude"]})
    assert r.status_code == 200
    body = r.json()
    board = {row["agent"]: row for row in body["leaderboard"]}
    assert board["claude"]["avg_score"] == 100.0
    assert board["opencode"]["avg_score"] == 0.0
    # claude ranks first
    assert body["quality_order"][0] == "claude"
    assert body["leaderboard"][0]["agent"] == "claude"


def test_bench_results_persisted(client, server, scored_agents):
    client.post("/api/bench/run", json={"agents": ["claude"]})
    res = client.get("/api/bench/results").json()
    assert res["leaderboard"][0]["agent"] == "claude"
    assert res["quality_order"]


def test_bench_feeds_quality_routing(client, server, scored_agents):
    client.post("/api/bench/run", json={"agents": ["opencode", "claude"]})
    # With quality preference, the fallback chain should follow the bench order
    client.put("/api/settings", json={"settings": {"routing": {"prefer": "quality"}}})
    try:
        chain = server.resolve_agent_chain("auto", primary="")
        assert chain[0] == "claude"  # bench winner leads
        assert set(chain) == set(server.KNOWN_AGENTS)
    finally:
        client.put("/api/settings", json={"settings": {"routing": {}}})


def test_bench_run_defaults_to_healthy_agents(client, server, monkeypatch):
    monkeypatch.setattr(server, "execute_agent", lambda a, m: "391 Paris s[::-1]")
    monkeypatch.setattr(server, "check_agent",
                        lambda n: {"name": n, "status": "online" if n == "claude" else "offline"})
    body = client.post("/api/bench/run", json={}).json()
    assert body["agents"] == ["claude"]
