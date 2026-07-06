# PyInstaller spec for the Agentic OS desktop app.
# Build:  pyinstaller AgenticOS.spec   (or run build.ps1)
# Produces a single versioned installer exe:  dist/AgenticOS-Setup-v<VERSION>.exe
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

try:
    VERSION = Path("VERSION").read_text(encoding="utf-8").strip() or "2.0.0"
except Exception:
    VERSION = "2.0.0"

block_cipher = None

# Read-only assets bundled into the app; seeded into %LOCALAPPDATA%\AgenticOS
# on first run (see desktop._resolve_home). VERSION ships too so the frozen
# app reports its version.
datas = [(d, d) for d in ("dashboard", "brain", "skills", "agents", "scheduler",
                          "prompts", "standards", "registry", "bench", "data", "docs")]
datas.append(("VERSION", "."))

# uvicorn/fastapi + our lazily-imported modules that static analysis can miss.
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("apscheduler")
    + ["server", "news_oracle", "voice_service", "branding", "brain.memory_search",
       "scheduler.scheduler", "feedparser", "pystray._win32", "PIL.Image",
       "PIL.ImageDraw", "PIL.ImageChops"]
)

a = Analysis(
    ["desktop.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "matplotlib"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-file build → a single double-clickable, versioned exe.
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name=f"AgenticOS-Setup-v{VERSION}",
    icon="AgenticOS.ico",   # crescent-moon exe / install icon
    console=False,          # GUI app — no console window
    upx=True,
    disable_windowed_traceback=False,
)
