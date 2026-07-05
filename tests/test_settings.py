"""Settings: merge semantics and API-key masking."""


def test_settings_roundtrip_and_masking(client, server):
    r = client.put("/api/settings", json={"settings": {
        "theme": "dark",
        "api_keys": {"openrouter": "sk-or-v1-supersecretvalue"},
    }})
    assert r.status_code == 200

    body = client.get("/api/settings").json()
    assert body["theme"] == "dark"
    # Masked in API response...
    assert body["api_keys"]["openrouter"] == "sk-o****"
    assert "supersecret" not in str(body)
    # ...but intact on disk
    raw = (server.BASE_DIR / "data" / "settings.json").read_text(encoding="utf-8")
    assert "sk-or-v1-supersecretvalue" in raw


def test_settings_merge_preserves_existing(client):
    client.put("/api/settings", json={"settings": {"dashboard": {"port": 9191}}})
    body = client.get("/api/settings").json()
    assert body["dashboard"]["port"] == 9191
    assert body["theme"] == "dark"  # from previous test, not clobbered
