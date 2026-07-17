#!/usr/bin/env python3
"""Agentic OS — desktop launcher.

Runs the FastAPI server in a background thread and presents a system-tray
icon plus (optionally) a native window. Tray and window libraries are
optional: if they're missing we fall back to opening the default browser,
so `python desktop.py` always works.
"""
import argparse
import json
import os
import shutil
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Pure app-asset dirs: refreshed on every version upgrade so the packaged app
# never serves a stale dashboard. UI staleness here caused blank/white screens.
_UI_DIRS = ["dashboard", "docs"]
# User/runtime dirs: seeded once, never clobbered (they hold your data).
_DATA_DIRS = ["brain", "skills", "agents", "scheduler", "prompts",
              "standards", "registry", "bench", "data"]


def _resolve_home() -> Path:
    """Where runtime state lives. In a packaged build, read-only assets ship
    inside the bundle (sys._MEIPASS) but writable data must go to a persistent
    per-user dir. Data dirs are seeded once; UI dirs are refreshed whenever the
    bundled version changes, so upgrades actually update the dashboard."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).parent

    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    home = Path(base) / "AgenticOS"
    home.mkdir(parents=True, exist_ok=True)
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))

    for d in _DATA_DIRS:
        src, dst = bundle / d, home / d
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)

    try:
        bundled_ver = (bundle / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        bundled_ver = ""
    marker = home / ".seeded_version"
    seeded_ver = marker.read_text(encoding="utf-8").strip() if marker.exists() else ""
    ui_up_to_date = bool(bundled_ver) and bundled_ver == seeded_ver
    for d in _UI_DIRS:
        src, dst = bundle / d, home / d
        if src.exists() and (not dst.exists() or not ui_up_to_date):
            # Overwrite in place (dirs_exist_ok) rather than rmtree+copytree:
            # on Windows the just-deleted dir can linger briefly and the
            # recreate then fails with FileExistsError (WinError 183).
            shutil.copytree(src, dst, dirs_exist_ok=True)
    if bundled_ver:
        marker.write_text(bundled_ver, encoding="utf-8")
    return home


def _ensure_stdio(home: Path) -> None:
    """A windowed (console=False) exe launched by double-click has NO console:
    sys.stdout/sys.stderr are None, which crashes uvicorn's logging setup
    (sys.stdout.isatty()). Point them at a log file so logging works and
    crashes are diagnosable."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        log_dir = home / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        stream = open(log_dir / "app.log", "a", encoding="utf-8", buffering=1)
    except Exception:
        stream = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


if getattr(sys, "frozen", False):
    # Redirect stdio to a log FIRST, before any seeding, so every startup error
    # (incl. failures inside _resolve_home) is captured rather than silently
    # crashing a windowed exe that has no console.
    _home = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "AgenticOS"
    try:
        _home.mkdir(parents=True, exist_ok=True)
        _ensure_stdio(_home)
    except Exception:
        pass
    try:
        os.environ.setdefault("AGENTIC_OS_HOME", str(_resolve_home()))
    except Exception:
        import traceback
        traceback.print_exc()   # goes to the log; seeding is best-effort
        os.environ.setdefault("AGENTIC_OS_HOME", str(_home))

BASE_DIR = Path(os.environ.get("AGENTIC_OS_HOME") or Path(__file__).parent).resolve()


def configured_port(default: int = 8080) -> int:
    sf = BASE_DIR / "data" / "settings.json"
    if sf.exists():
        try:
            return int(json.loads(sf.read_text(encoding="utf-8")).get("dashboard", {}).get("port", default))
        except Exception:
            pass
    return default


# ─── Server thread (testable core) ────────────────────────────────

def make_server(host: str = "127.0.0.1", port: int = 8080):
    """Build a uvicorn Server bound to the FastAPI app (not yet started).

    use_colors=False keeps uvicorn's formatter from probing sys.stdout.isatty(),
    which crashes in a windowed exe where stdout can be None."""
    import uvicorn
    import server as server_module
    config = uvicorn.Config(server_module.app, host=host, port=port,
                            log_level="info", use_colors=False)
    return uvicorn.Server(config)


def start_server_thread(host: str = "127.0.0.1", port: int = 8080):
    """Start the server in a daemon thread. Returns (thread, server)."""
    server = make_server(host, port)
    # install_signal_handlers=False so it can run off the main thread
    server.config.install_signal_handlers = False
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread, server


def wait_until_ready(url: str, timeout: float = 20.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


# ─── Tray + window (optional, GUI) ────────────────────────────────

def _tray_image():
    from branding import moon_image  # crescent-moon logo
    return moon_image(64)


def _launch_minimized_setting() -> bool:
    sf = BASE_DIR / "data" / "settings.json"
    if sf.exists():
        try:
            return bool(json.loads(sf.read_text(encoding="utf-8")).get("system", {}).get("launch_minimized", False))
        except Exception:
            pass
    return False


def run_desktop(host: str = "127.0.0.1", port: int = None, minimized: bool = False):
    port = port or configured_port()
    minimized = minimized or _launch_minimized_setting()
    url = f"http://{host}:{port}"
    print(f"Agentic OS starting on {url} …")
    start_server_thread(host, port)
    if not wait_until_ready(url + "/"):
        print("WARNING: server did not become ready in time")

    def open_dashboard(*_):
        try:
            import webview  # pywebview
            if not getattr(open_dashboard, "_win", None):
                open_dashboard._win = webview.create_window("Agentic OS", url, width=1280, height=860)
                webview.start()  # blocks until the window closes
            else:
                webbrowser.open(url)
        except Exception:
            webbrowser.open(url)

    try:
        import pystray
        icon = pystray.Icon(
            "agentic-os", _tray_image(), "Agentic OS",
            menu=pystray.Menu(
                pystray.MenuItem("Open Dashboard", lambda *_: webbrowser.open(url), default=True),
                pystray.MenuItem("Open in App Window", open_dashboard),
                pystray.MenuItem("Quit", lambda icon, *_: icon.stop()),
            ),
        )
        if not minimized:
            webbrowser.open(url)
        icon.run()  # blocks on the main thread until Quit
    except Exception as e:
        # No tray available — just open the browser and idle.
        print(f"System tray unavailable ({e}); opening browser. Ctrl+C to quit.")
        if not minimized:
            webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description="Agentic OS desktop app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--minimized", action="store_true",
                        help="Start to tray without opening a window")
    args = parser.parse_args()
    run_desktop(host=args.host, port=args.port, minimized=args.minimized)


if __name__ == "__main__":
    main()
