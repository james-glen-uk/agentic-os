# PyInstaller spec for Agentic OS desktop app.
# Build:  pyinstaller AgenticOS.spec   (or run build.ps1)
# Produces dist/AgenticOS/AgenticOS.exe (onedir — fast startup, easy to inspect).

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Read-only assets bundled into the app; seeded into %LOCALAPPDATA%\AgenticOS
# on first run (see desktop._resolve_home).
datas = [
    ("dashboard", "dashboard"),
    ("brain", "brain"),
    ("skills", "skills"),
    ("agents", "agents"),
    ("scheduler", "scheduler"),
    ("prompts", "prompts"),
    ("standards", "standards"),
    ("registry", "registry"),
    ("bench", "bench"),
    ("data", "data"),
    ("docs", "docs"),
]

# uvicorn/fastapi and our own lazily-imported modules that PyInstaller's static
# analysis can miss.
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("apscheduler")
    + ["server", "news_oracle", "voice_service", "brain.memory_search",
       "scheduler.scheduler", "feedparser", "pystray._win32", "PIL.Image",
       "PIL.ImageDraw"]
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

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="AgenticOS",
    console=False,          # GUI app — no console window
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, name="AgenticOS",
)
