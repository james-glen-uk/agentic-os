"""Shareable save-file export/import: secrets excluded, deps reported."""
import json
import tarfile


def test_export_creates_file_and_manifest(client, server):
    r = client.post("/api/export")
    assert r.status_code == 200
    body = r.json()
    assert body["file"].endswith(".tar.gz")
    assert set(["ceo", "builder"]).issubset(set(body["manifest"]["roles"]))
    assert "news-oracle" in body["manifest"]["skills"]
    assert body["file"] in [e["name"] for e in client.get("/api/exports").json()["exports"]]


def test_export_excludes_secrets(client, server):
    client.put("/api/settings", json={"settings": {"api_keys": {"gemini": "sk-secret-123"}}})
    name = client.post("/api/export").json()["file"]
    archive = server.EXPORT_DIR / name

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        assert "settings.template.json" in names
        assert not any("settings.json" in n and "template" not in n for n in names)
        tmpl = json.loads(tar.extractfile("settings.template.json").read())
    assert "api_keys" not in tmpl
    # And the secret must not appear anywhere in the archive bytes
    assert b"sk-secret-123" not in archive.read_bytes()


def test_import_roundtrip_restores_config(client, server):
    brain = server.BASE_DIR / "brain" / "memory.md"
    brain.write_text("# Memory\n\nThe teal narwhal marker.\n", encoding="utf-8")
    name = client.post("/api/export").json()["file"]

    brain.write_text("# wiped\n", encoding="utf-8")  # simulate loss
    r = client.post("/api/import", json={"file": name})
    assert r.status_code == 200
    assert r.json()["applied"] is True
    assert "teal narwhal" in brain.read_text(encoding="utf-8")


def test_import_preserves_existing_secrets(client, server):
    # Export made with no secret
    name = client.post("/api/export").json()["file"]
    # Importer already has a key configured
    client.put("/api/settings", json={"settings": {"api_keys": {"openrouter": "keep-me"}}})
    client.post("/api/import", json={"file": name})
    raw = (server.BASE_DIR / "data" / "settings.json").read_text(encoding="utf-8")
    assert "keep-me" in raw  # secret never overwritten by import


def test_import_reports_missing_dependencies(client, server, monkeypatch):
    name = client.post("/api/export").json()["file"]
    monkeypatch.setattr(server.shutil, "which", lambda _: None)  # nothing installed
    report = client.post("/api/import", json={"file": name, "apply": False}).json()
    assert report["applied"] is False
    assert "opencode" in report["missing_dependencies"]["agent_clis"]


def test_import_validation(client):
    assert client.post("/api/import", json={"file": "../etc/passwd"}).status_code == 400
    assert client.post("/api/import", json={"file": "nope.tar.gz"}).status_code == 404
