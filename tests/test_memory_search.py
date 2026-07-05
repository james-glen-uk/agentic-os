"""FTS5 memory search: reindex and query over brain content."""


def test_reindex_and_search(client):
    r = client.put("/api/brain/memory.md", json={"content": "# Memory\n\nThe quixotic flamingo project uses FastAPI.\n"})
    assert r.status_code == 200

    assert client.post("/api/memory/reindex").json()["status"] == "reindexed"

    body = client.get("/api/memory/search", params={"q": "flamingo"}).json()
    assert body["query"] == "flamingo"
    assert len(body["results"]) >= 1
    assert any("flamingo" in str(res).lower() for res in body["results"])


def test_empty_query_returns_empty(client):
    body = client.get("/api/memory/search", params={"q": ""}).json()
    assert body["results"] == []


def test_entities_endpoint(client):
    r = client.get("/api/memory/entities")
    assert r.status_code == 200
    assert "entities" in r.json()
