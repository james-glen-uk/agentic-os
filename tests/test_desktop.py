"""Desktop launcher: server-in-thread boots and serves, port config."""
import urllib.request

import pytest


def test_configured_port_reads_settings(server, monkeypatch):
    import desktop
    monkeypatch.setattr(desktop, "BASE_DIR", server.BASE_DIR)
    (server.BASE_DIR / "data").mkdir(exist_ok=True)
    (server.BASE_DIR / "data" / "settings.json").write_text('{"dashboard": {"port": 9137}}', encoding="utf-8")
    assert desktop.configured_port() == 9137


def test_configured_port_default(server, monkeypatch, tmp_path):
    import desktop
    monkeypatch.setattr(desktop, "BASE_DIR", tmp_path)  # no settings file
    assert desktop.configured_port(default=8080) == 8080


def test_server_thread_serves(server):
    """The launcher's server thread actually serves the dashboard."""
    import desktop
    port = 8231
    thread, userver = desktop.start_server_thread("127.0.0.1", port)
    try:
        assert desktop.wait_until_ready(f"http://127.0.0.1:{port}/", timeout=20)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as r:
            assert r.status == 200
    finally:
        userver.should_exit = True
        thread.join(timeout=10)


def test_wait_until_ready_times_out_fast(server):
    import desktop
    # Nothing listening on this port → returns False without hanging
    assert desktop.wait_until_ready("http://127.0.0.1:8199/", timeout=1.0) is False
