"""Start-on-boot + tray settings (registry mocked — never touch real HKCU)."""
import pytest


@pytest.fixture()
def fake_startup(server, monkeypatch):
    """Swap the real registry backend for an in-memory one so tests never
    write to the user's actual Windows startup registry."""
    backend = server._MemoryStartupBackend(supported=True)
    monkeypatch.setattr(server, "_startup_backend", backend)
    return backend


def test_get_startup_defaults(client, fake_startup):
    body = client.get("/api/system/startup").json()
    assert body["supported"] is True
    assert body["start_on_boot"] is False
    assert body["minimize_to_tray"] is True  # default on


def test_enable_and_disable_start_on_boot(client, fake_startup):
    r = client.put("/api/system/startup", json={"start_on_boot": True})
    assert r.status_code == 200
    assert r.json()["start_on_boot"] is True
    assert fake_startup.is_enabled() is True

    r = client.put("/api/system/startup", json={"start_on_boot": False})
    assert r.json()["start_on_boot"] is False
    assert fake_startup.is_enabled() is False


def test_tray_prefs_persist(client, fake_startup, server):
    client.put("/api/system/startup", json={"minimize_to_tray": False, "launch_minimized": True})
    body = client.get("/api/system/startup").json()
    assert body["minimize_to_tray"] is False
    assert body["launch_minimized"] is True
    # persisted to settings.json, secrets untouched
    import json
    saved = json.loads((server.BASE_DIR / "data" / "settings.json").read_text(encoding="utf-8"))
    assert saved["system"]["launch_minimized"] is True


def test_unsupported_platform_rejects_boot_toggle(client, server, monkeypatch):
    monkeypatch.setattr(server, "_startup_backend", server._MemoryStartupBackend(supported=False))
    assert client.put("/api/system/startup", json={"start_on_boot": True}).status_code == 400
    # but tray prefs still work
    assert client.put("/api/system/startup", json={"minimize_to_tray": True}).status_code == 200


def test_startup_command_is_minimized(server):
    cmd = server._startup_command()
    assert "--minimized" in cmd


def test_settings_api_keys_preserved_across_startup_write(client, fake_startup, server):
    client.put("/api/settings", json={"settings": {"api_keys": {"gemini": "keep-secret"}}})
    client.put("/api/system/startup", json={"launch_minimized": True})
    import json
    saved = json.loads((server.BASE_DIR / "data" / "settings.json").read_text(encoding="utf-8"))
    assert saved["api_keys"]["gemini"] == "keep-secret"
