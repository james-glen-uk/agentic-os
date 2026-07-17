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


def test_make_server_survives_null_stdio(server, monkeypatch, tmp_path):
    """Regression: double-clicking the windowed exe gives the process NO
    console, so sys.stdout/sys.stderr are None — uvicorn's logging config then
    crashed on sys.stdout.isatty() (ValueError: Unable to configure formatter).
    _ensure_stdio must restore usable streams and make_server must not raise."""
    import sys
    import desktop
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    desktop._ensure_stdio(tmp_path)
    assert sys.stdout is not None and sys.stderr is not None
    assert (tmp_path / "logs" / "app.log").exists()

    srv = desktop.make_server("127.0.0.1", 8232)  # must not raise
    assert srv.config.use_colors is False

    print("stdio works again")  # lands in the log file, must not raise
    sys.stdout.flush()
    assert "stdio works again" in (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")


def test_make_server_null_stdout_without_ensure(server, monkeypatch):
    """Even without _ensure_stdio (belt), use_colors=False (suspenders) keeps
    uvicorn's Config from probing isatty on a None stdout."""
    import sys
    import desktop
    monkeypatch.setattr(sys, "stdout", None)
    desktop.make_server("127.0.0.1", 8233)  # must not raise
