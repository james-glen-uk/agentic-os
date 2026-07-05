"""News Oracle: clustering, refresh endpoint, topics endpoint, data age."""
import json

import pytest

SAMPLE_ENTRIES = [
    {"title": "OpenAI releases new agent framework for developers", "link": "https://a/1", "source": "TechCrunch", "published": "x"},
    {"title": "New agent framework from OpenAI changes developer tooling", "link": "https://a/2", "source": "Verge", "published": "x"},
    {"title": "Developers react to OpenAI agent framework launch", "link": "https://a/3", "source": "HN", "published": "x"},
    {"title": "Quantum computing milestone reached by research lab", "link": "https://b/1", "source": "Ars", "published": "x"},
    {"title": "Research lab announces quantum computing breakthrough", "link": "https://b/2", "source": "HN", "published": "x"},
    {"title": "Solar panel efficiency record broken", "link": "https://c/1", "source": "Verge", "published": "x"},
]


def test_cluster_topics_groups_and_ranks(server):
    import news_oracle
    topics = news_oracle.cluster_topics(SAMPLE_ENTRIES)
    assert topics[0]["rank"] == 1
    assert topics[0]["count"] == 3  # the OpenAI cluster is biggest
    assert {h["link"] for h in topics[0]["headlines"]} == {"https://a/1", "https://a/2", "https://a/3"}
    assert topics[1]["count"] == 2  # quantum cluster
    counts = [t["count"] for t in topics]
    assert counts == sorted(counts, reverse=True)


@pytest.fixture()
def stub_feeds(server, monkeypatch):
    import news_oracle
    monkeypatch.setattr(news_oracle, "fetch_entries", lambda feeds: list(SAMPLE_ENTRIES))


def test_refresh_persists_and_returns_topics(client, server, stub_feeds):
    body = client.post("/api/news/refresh").json()
    assert body["entry_count"] == len(SAMPLE_ENTRIES)
    assert body["topics"][0]["count"] == 3

    news_file = server.NEWS_DIR / f"{body['date']}.json"
    assert news_file.exists()
    on_disk = json.loads(news_file.read_text(encoding="utf-8"))
    assert on_disk["topics"] == body["topics"]


def test_topics_endpoint_with_age(client, stub_feeds):
    client.post("/api/news/refresh")
    body = client.get("/api/news/topics").json()
    assert body["topics"]
    assert body["age_hours"] is not None and body["age_hours"] < 1
    assert body["date"] in body["available_dates"]


def test_topics_date_validation(client):
    assert client.get("/api/news/topics", params={"date": "not-a-date"}).status_code == 400
    body = client.get("/api/news/topics", params={"date": "1999-01-01"}).json()
    assert body["topics"] == []


def test_llm_enrichment_adds_summaries(client, server, stub_feeds, monkeypatch):
    client.put("/api/settings", json={"settings": {"news": {"use_llm": True}}})
    monkeypatch.setattr(server, "execute_agent",
                        lambda a, m: '{"1": "Big agent framework news.", "2": "Quantum progress."}')
    try:
        body = client.post("/api/news/refresh").json()
        assert body["topics"][0]["summary"] == "Big agent framework news."
    finally:
        client.put("/api/settings", json={"settings": {"news": {"use_llm": False}}})


def test_scheduled_job_registered(client):
    jobs = client.get("/api/scheduler/jobs").json()
    oracle = next((j for j in jobs if j.get("skill") == "news-oracle"), None)
    assert oracle and oracle["enabled"]
