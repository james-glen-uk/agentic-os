"""Multi-conversation chat: create/list/get/delete, auto-create on first
message, and legacy chat-history.json migration."""
import json

import pytest


@pytest.fixture()
def scripted_agent(server, monkeypatch):
    def fake(agent, message):
        return f"ok from {agent}"

    monkeypatch.setattr(server, "execute_agent", fake)


def test_create_and_list_conversation(client):
    r = client.post("/api/conversations", json={"title": "Test thread"})
    assert r.status_code == 200
    conv = r.json()
    assert conv["title"] == "Test thread"
    assert conv["messages"] == []

    ids = [c["id"] for c in client.get("/api/conversations").json()["conversations"]]
    assert conv["id"] in ids


def test_chat_without_conversation_id_auto_creates(client, scripted_agent):
    r = client.post("/api/chat", json={"agent": "opencode", "message": "hello there"})
    body = r.json()
    assert r.status_code == 200
    conv_id = body["conversation_id"]
    assert conv_id

    conv = client.get(f"/api/conversations/{conv_id}").json()
    assert len(conv["messages"]) == 2
    assert conv["messages"][0]["content"] == "hello there"
    assert conv["title"].startswith("hello there")


def test_chat_with_existing_conversation_id_appends(client, scripted_agent):
    conv = client.post("/api/conversations", json={"title": "Existing"}).json()
    r = client.post("/api/chat", json={
        "agent": "opencode", "message": "second message", "conversation_id": conv["id"],
    })
    assert r.json()["conversation_id"] == conv["id"]

    fetched = client.get(f"/api/conversations/{conv['id']}").json()
    assert len(fetched["messages"]) == 2
    # title was explicitly set at creation, so it should not be overwritten
    assert fetched["title"] == "Existing"

    all_ids = [c["id"] for c in client.get("/api/conversations").json()["conversations"]]
    assert all_ids.count(conv["id"]) == 1


def test_delete_conversation(client):
    conv = client.post("/api/conversations", json={}).json()
    assert client.delete(f"/api/conversations/{conv['id']}").status_code == 200
    assert client.get(f"/api/conversations/{conv['id']}").status_code == 404
    assert client.delete(f"/api/conversations/{conv['id']}").status_code == 404


def test_get_missing_conversation_404(client):
    assert client.get("/api/conversations/zzzzzzzz").status_code == 404


def test_chat_history_backward_compat_returns_latest(client, scripted_agent):
    older = client.post("/api/conversations", json={"title": "Older"}).json()
    client.post("/api/chat", json={
        "agent": "opencode", "message": "in older thread", "conversation_id": older["id"],
    })
    newer_id = client.post("/api/chat", json={"agent": "opencode", "message": "in newest thread"}).json()["conversation_id"]

    history = client.get("/api/chat/history").json()
    assert history["messages"][0]["content"] == "in newest thread"
    assert newer_id != older["id"]


def test_legacy_chat_history_migration(server):
    legacy_file = server.BASE_DIR / "data" / "chat-history.json"
    conversations_file = server.BASE_DIR / "data" / "conversations.json"
    migrated_marker = server.BASE_DIR / "data" / "chat-history.json.migrated"

    conversations_file.unlink(missing_ok=True)
    migrated_marker.unlink(missing_ok=True)
    legacy_file.write_text(json.dumps({"messages": [
        {"id": "aaaa1111", "role": "user", "agent": "claude", "content": "legacy msg", "timestamp": "2026-01-01T00:00:00+00:00"},
    ]}), encoding="utf-8")

    server.migrate_legacy_chat_history()

    assert not legacy_file.exists()
    assert migrated_marker.exists()
    data = json.loads(conversations_file.read_text(encoding="utf-8"))
    assert any(c["title"] == "Imported conversation" and c["messages"][0]["content"] == "legacy msg"
               for c in data["conversations"])

    # Idempotent: running again with no legacy file left is a no-op
    server.migrate_legacy_chat_history()
