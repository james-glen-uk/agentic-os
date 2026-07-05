"""Brain file endpoints: list, read, write, and path-traversal rejection."""


def test_list_brain_files(client):
    r = client.get("/api/brain")
    assert r.status_code == 200
    assert "memory.md" in r.json()


def test_get_missing_file_404(client):
    assert client.get("/api/brain/nope.md").status_code == 404


def test_traversal_rejected(client):
    assert client.get("/api/brain/..%5C..%5Csecrets.md").status_code == 400
    r = client.put("/api/brain/..evil.md", json={"content": "x"})
    assert r.status_code == 400


def test_write_then_read(client):
    r = client.put("/api/brain/constraints.md", json={"content": "# Constraints\n\nBudget: $0\n"})
    assert r.status_code == 200
    r = client.get("/api/brain/constraints.md")
    assert "Budget: $0" in r.json()["content"]
