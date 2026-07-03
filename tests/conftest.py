"""Shared fixtures: run the app against an isolated temp copy of the repo.

AGENTIC_OS_HOME points server.py and scheduler/scheduler.py at a temp
directory so tests never touch real runtime state (data/, brain/, audit/...).
The env var must be set before server.py is imported, hence the session
fixture ordering below.
"""
import importlib
import os
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories copied into the isolated home (templates the app reads)
TEMPLATE_DIRS = ["dashboard", "brain", "skills", "scheduler", "prompts", "standards", "registry", "agents"]
# Runtime directories created empty
RUNTIME_DIRS = ["data", "data/kanban", "audit", "backups"]


@pytest.fixture(scope="session")
def app_home(tmp_path_factory):
    home = tmp_path_factory.mktemp("agentic-home")
    for d in TEMPLATE_DIRS:
        src = REPO_ROOT / d
        if src.exists():
            shutil.copytree(src, home / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for d in RUNTIME_DIRS:
        (home / d).mkdir(parents=True, exist_ok=True)
    return home


@pytest.fixture(scope="session")
def server(app_home):
    os.environ["AGENTIC_OS_HOME"] = str(app_home)
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import brain.memory_search as memory_mod
    import scheduler.scheduler as sched_mod
    import server as server_mod

    # Reload in case any module was imported before the env var was set
    importlib.reload(memory_mod)
    importlib.reload(sched_mod)
    server_mod = importlib.reload(server_mod)
    assert server_mod.BASE_DIR == app_home.resolve()
    return server_mod


@pytest.fixture()
def client(server):
    from fastapi.testclient import TestClient

    # No context manager: lifespan (and thus the background scheduler) stays off
    return TestClient(server.app)
