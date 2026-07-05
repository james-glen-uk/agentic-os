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
import threading
import time
import webbrowser
from pathlib import Path

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
    """Build a uvicorn Server bound to the FastAPI app (not yet started)."""
    import uvicorn
    import server as server_module
    config = uvicorn.Config(server_module.app, host=host, port=port, log_level="info")
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
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, 58, 58), fill=(217, 119, 87, 255))   # brand orange
    d.text((22, 20), "A", fill=(255, 255, 255, 255))
    return img


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
