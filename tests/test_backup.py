"""Backup create/list and restore input validation."""


def test_backup_create_and_list(client):
    r = client.post("/api/backup")
    assert r.status_code == 200
    name = r.json()["file"]
    assert name.endswith(".tar.gz")
    assert name in [b["name"] for b in client.get("/api/backups").json()]


def test_restore_validation(client):
    assert client.post("/api/backup/restore", json={"file": "../../etc/passwd"}).status_code == 400
    assert client.post("/api/backup/restore", json={"file": "missing.tar.gz"}).status_code == 404


def test_restore_roundtrip(client, server):
    marker = server.BASE_DIR / "brain" / "identity.md"
    original = marker.read_text(encoding="utf-8")

    backup = client.post("/api/backup").json()["file"]
    marker.write_text(original + "\nTAMPERED\n", encoding="utf-8")
    r = client.post("/api/backup/restore", json={"file": backup})
    assert r.status_code == 200
    assert marker.read_text(encoding="utf-8") == original
