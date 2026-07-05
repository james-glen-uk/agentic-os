"""agent_data_dir(): per-platform resolution and existing-dir preference."""
from pathlib import Path


def test_default_is_xdg_location_when_nothing_exists(server, monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(server, "_IS_WINDOWS", False)
    assert server.agent_data_dir("opencode") == tmp_path / ".local" / "share" / "opencode"


def test_xdg_data_home_wins_when_it_exists(server, monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    xdg = tmp_path / "xdg"
    (xdg / "opencode").mkdir(parents=True)
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    assert server.agent_data_dir("opencode") == xdg / "opencode"


def test_windows_localappdata_used_when_it_exists(server, monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    local = tmp_path / "AppData" / "Local"
    (local / "opencode").mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setattr(server, "_IS_WINDOWS", True)
    assert server.agent_data_dir("opencode") == local / "opencode"


def test_hermes_and_gemini_are_home_dotdirs(server, monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    assert server.agent_data_dir("hermes") == tmp_path / ".hermes"
    assert server.agent_data_dir("gemini") == tmp_path / ".gemini"


def test_status_and_health_endpoints_work(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    names = {a["name"] for a in r.json()["agents"]}
    assert {"opencode", "hermes", "gemini"} <= names

    r = client.get("/api/agents/health")
    assert r.status_code == 200
