#!/usr/bin/env python3
"""
Agentic OS — FastAPI Backend
Multi-agent orchestration server for opencode, Hermes, Gemini CLI
"""
import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import tarfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

log = logging.getLogger("agentic_os")

_scheduler_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_instance
    log_agent_cli_table(probe_agent_clis())
    try:
        from scheduler.scheduler import CronScheduler
        _scheduler_instance = CronScheduler()
        _scheduler_instance.start()
        log.info("Event-driven scheduler started")
    except Exception as e:
        log.warning("Scheduler not available: %s", e)
    yield
    if _scheduler_instance:
        try:
            _scheduler_instance.stop()
        except Exception:
            pass

app = FastAPI(title="Agentic OS", version="1.1.0", lifespan=lifespan)

# ─── Platform-aware agent CLI locations ──────────────────────────

# Module-level so tests can patch it without touching global os.name
# (patching os.name breaks pathlib flavour selection cross-platform)
_IS_WINDOWS = os.name == "nt"

def agent_data_dir(agent: str) -> Path:
    """Resolve an agent CLI's data directory across platforms.

    Returns the first existing candidate, else the platform default,
    so callers can still show a sensible path when the CLI is absent.
    """
    home = Path.home()
    if agent == "opencode":
        candidates = []
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            candidates.append(Path(xdg) / "opencode")
        if _IS_WINDOWS:
            local = os.environ.get("LOCALAPPDATA")
            if local:
                candidates.append(Path(local) / "opencode")
        candidates.append(home / ".local" / "share" / "opencode")
    elif agent in ("hermes", "gemini"):
        candidates = [home / f".{agent}"]
    else:
        candidates = [home / f".{agent}"]
    for c in candidates:
        if c.exists():
            return c
    return candidates[-1]

# Load OpenRouter API key from Hermes .env
HERMES_ENV = agent_data_dir("hermes") / ".env"
if HERMES_ENV.exists():
    for line in HERMES_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k == "OPENROUTER_API_KEY":
                os.environ[k] = v  # last value wins (matches shell sourcing)

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root of all runtime state; AGENTIC_OS_HOME overrides for tests/custom installs
BASE_DIR = Path(os.environ.get("AGENTIC_OS_HOME") or Path(__file__).parent).resolve()

# ─── Models ───────────────────────────────────────────────────────

class BrainUpdate(BaseModel):
    content: str

class SkillRunRequest(BaseModel):
    input: Optional[str] = ""
    agent: Optional[str] = "auto"
    topic: Optional[str] = ""

class ScheduleJobRequest(BaseModel):
    name: str
    skill: str
    cron: str
    enabled: bool = True

class SettingsUpdate(BaseModel):
    settings: dict

class BackupRestoreRequest(BaseModel):
    file: str

class ChatRequest(BaseModel):
    agent: str
    message: str

# ─── Helper Functions ─────────────────────────────────────────────

def read_file(path: Path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

def write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    return True

def list_dir(path: Path):
    if not path.exists():
        return []
    return sorted([p.name for p in path.iterdir() if not p.name.startswith(".") and p.is_file()])

def get_timestamp():
    return datetime.now(timezone.utc).isoformat()

def append_audit(entry: dict):
    audit_file = BASE_DIR / "audit" / "audit.log"
    entry["timestamp"] = get_timestamp()
    entry["id"] = str(uuid.uuid4())[:8]
    with open(audit_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def safe_resolve(base: Path, user_path: str) -> Path:
    """Resolve a user-supplied path relative to base, preventing traversal."""
    resolved = (base / user_path).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise HTTPException(400, "Invalid path")
    return resolved

def safe_extractall(tar: tarfile.TarFile, path: Path):
    """Extract tar archive with path traversal protection."""
    for member in tar.getmembers():
        member_path = (path / member.name).resolve()
        if not str(member_path).startswith(str(path.resolve())):
            raise HTTPException(400, f"Blocked path traversal: {member.name}")
    tar.extractall(path=path)

# ─── Security Headers Middleware ─────────────────────────────────

class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                extra = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ]
                # Only add CSP for non-API routes (dashboard HTML)
                path = scope.get("path", "")
                if not path.startswith("/api/"):
                    csp = (
                        b"default-src 'self'; "
                        b"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                        b"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                        b"font-src 'self' https://fonts.gstatic.com; "
                        b"img-src 'self' data:; "
                        b"connect-src 'self' http://127.0.0.1:* http://localhost:*; "
                        b"frame-ancestors 'none'"
                    )
                    extra.append((b"content-security-policy", csp))
                message["headers"] = list(headers) + extra
            await send(message)

        await self.app(scope, receive, send_with_headers)

app.add_middleware(SecurityHeadersMiddleware)

# ─── Settings / Logging / Boot-time CLI validation ──────────────────

def load_settings() -> dict:
    sf = BASE_DIR / "data" / "settings.json"
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def setup_logging():
    level_name = str(load_settings().get("logging", {}).get("level", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

setup_logging()

AGENT_CLI_HINTS = {
    "opencode": "npm install -g @opencode/cli",
    "hermes": "https://github.com/NousResearch/hermes-agent",
    "gemini": "npm install -g @google/gemini-cli",
    "claude": "https://claude.com/claude-code",
}

_agent_cli_status: dict = {}

def probe_agent_clis() -> dict:
    """Boot-time probe: which agent CLIs exist, and their versions."""
    enabled_map = load_settings().get("agents", {})
    results = {}
    for name in AGENT_CLI_HINTS:
        enabled = enabled_map.get(name, True)
        path = shutil.which(name) if enabled else None
        version = None
        if path:
            try:
                proc = subprocess.run(
                    [name, "--version"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=10,
                )
                first_line = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
                version = first_line[0][:80] if first_line else None
            except Exception:
                pass
        results[name] = {"enabled": enabled, "found": path is not None,
                         "path": path, "version": version}
    _agent_cli_status.clear()
    _agent_cli_status.update(results)
    return results

def log_agent_cli_table(results: dict):
    log.info("Agent CLI availability:")
    for name, r in results.items():
        if not r["enabled"]:
            log.info("  %-9s disabled in settings", name)
        elif r["found"]:
            log.info("  %-9s OK  %s", name, r["version"] or r["path"])
        else:
            log.warning("  %-9s missing — install: %s", name, AGENT_CLI_HINTS[name])

# ─── Agent Discovery (instant filesystem checks) ────────────────────

# Canonical agent list: the free-tier trio + Claude Code (premium)
KNOWN_AGENTS = ["opencode", "hermes", "gemini", "claude"]

def load_agent_config(agent: str) -> dict:
    p = BASE_DIR / "agents" / agent / f"{agent}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def check_agent(name: str) -> dict:
    """Instant filesystem-based check. No subprocess needed."""
    try:
        if name in ("opencode", "hermes", "claude"):
            exists = shutil.which(name) is not None
            status = "online" if exists else "offline"
        elif name == "gemini":
            # Gemini has valid OAuth tokens logged in
            oauth = agent_data_dir("gemini") / "oauth_creds.json"
            exists = shutil.which("gemini") is not None
            logged_in = oauth.exists() and "ya29" in oauth.read_text(encoding="utf-8", errors="replace")
            status = "online" if exists and logged_in else "offline" if not exists else "warning"
        else:
            status = "offline"
    except Exception:
        status = "offline"
    return {"name": name, "status": status}

# ─── Routes: Status ───────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    agents = [check_agent(a) for a in KNOWN_AGENTS]
    skills_dir = BASE_DIR / "skills"
    skills_count = 0
    if skills_dir.exists():
        # skills are directories (skills/<name>/SKILL.md), not files
        skills_count = len([p for p in skills_dir.iterdir()
                            if p.is_dir() and not p.name.startswith("_")])
    return {
        "status": "healthy",
        "agents": agents,
        "skills_count": skills_count,
        "uptime": time.time(),
    }

# ─── Routes: Brain ────────────────────────────────────────────────

@app.get("/api/brain")
def list_brain():
    brain_dir = BASE_DIR / "brain"
    if not brain_dir.exists():
        return {}
    files = sorted([p.name for p in brain_dir.iterdir() if p.name.endswith(".md") and p.is_file()])
    brain_data = {}
    for f in files:
        path = brain_dir / f
        brain_data[f] = read_file(path)
    return brain_data

@app.get("/api/brain/{file_name}")
def get_brain_file(file_name: str):
    if ".." in file_name or "/" in file_name:
        raise HTTPException(400, "Invalid file name")
    path = BASE_DIR / "brain" / file_name
    if not path.exists() or path.is_dir():
        raise HTTPException(404, "File not found")
    return {"name": file_name, "content": read_file(path)}

@app.put("/api/brain/{file_name}")
def update_brain_file(file_name: str, data: BrainUpdate):
    if ".." in file_name or "/" in file_name:
        raise HTTPException(400, "Invalid file name")
    path = BASE_DIR / "brain" / file_name
    write_file(path, data.content)
    append_audit({"action": "brain_update", "file": file_name})
    return {"status": "ok", "file": file_name}

# ─── Routes: Skills ───────────────────────────────────────────────

@app.get("/api/skills")
def list_skills():
    skills = []
    for d in sorted((BASE_DIR / "skills").iterdir()):
        if d.is_dir() and not d.name.startswith("_"):
            skill_md = read_file(d / "SKILL.md")
            learnings = read_file(d / "learnings.md")
            eval_data = {}
            eval_path = d / "eval.json"
            if eval_path.exists():
                eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
            score_history = []
            score_path = d / "score-history.json"
            if score_path.exists():
                score_history = json.loads(score_path.read_text(encoding="utf-8"))
            skills.append({
                "name": d.name,
                "description": skill_md[:200] if skill_md else "",
                "has_learnings": bool(learnings),
                "eval_criteria": eval_data.get("criteria", []),
                "scores": score_history,
            })
    return skills

@app.get("/api/skills/{name}")
def get_skill(name: str):
    if ".." in name or "/" in name:
        raise HTTPException(400, "Invalid skill name")
    path = BASE_DIR / "skills" / name
    if not path.exists():
        raise HTTPException(404, "Skill not found")
    return {
        "name": name,
        "skill": read_file(path / "SKILL.md"),
        "learnings": read_file(path / "learnings.md"),
        "eval": json.loads((path / "eval.json").read_text(encoding="utf-8")) if (path / "eval.json").exists() else {},
        "score_history": json.loads((path / "score-history.json").read_text(encoding="utf-8")) if (path / "score-history.json").exists() else [],
        "context": [f.name for f in (path / "context").iterdir()] if (path / "context").exists() else [],
    }

@app.post("/api/skills/{name}/run")
def run_skill(name: str, req: Optional[SkillRunRequest] = None):
    if ".." in name or "/" in name:
        raise HTTPException(400, "Invalid skill name")
    path = BASE_DIR / "skills" / name
    if not path.exists():
        raise HTTPException(404, "Skill not found")

    agent_choice = req.agent if req else "auto"
    skill_input = req.input if req else ""

    # Read skill files
    skill_md = read_file(path / "SKILL.md")
    learnings = read_file(path / "learnings.md")

    # Determine which agent based on skill type
    if agent_choice == "auto":
        devops_keywords = ["devops", "audit", "deploy", "k8s", "gcp", "infra", "terraform"]
        research_keywords = ["research", "synthesis", "analyze", "search", "compare"]
        if any(k in name for k in devops_keywords):
            agent_choice = "opencode"
        elif any(k in name for k in research_keywords):
            agent_choice = "gemini"
        else:
            # Check SKILL.md for explicit agent assignment
            for line in skill_md.split('\n'):
                line = line.strip()
                if "Primary:" in line:
                    candidate = line.split(":")[-1].strip().lower()
                    if candidate in KNOWN_AGENTS:
                        agent_choice = candidate
                        break
            if agent_choice == "auto":
                agent_choice = "opencode"

    # Build prompt from skill instructions + learnings + user input
    prompt = f"Execute the '{name}' skill.\n\n"
    if skill_md:
        prompt += f"## Skill Instructions\n{skill_md}\n\n"
    if learnings and learnings.strip():
        prompt += f"## Past Learnings\n{learnings}\n\n"
    if skill_input:
        prompt += f"## User Input\n{skill_input}"

    run_id = str(uuid.uuid4())[:8]

    # Execute via fallback chain (explicit choice first, else routed primary)
    requested = (req.agent if req and req.agent else "auto") or "auto"
    chain = resolve_agent_chain(requested, primary=agent_choice)
    run_result = execute_with_fallback(chain, prompt)
    response_text = run_result["output"]
    agent_used = run_result["agent"] or agent_choice

    # Save output to learnings.md
    timestamp = get_timestamp()[:10]
    existing = read_file(path / "learnings.md")
    fallback_note = " (fallback)" if run_result["fallback_used"] and run_result["agent"] else ""
    new_entry = (
        f"\n## {timestamp} (Run {run_id})\n"
        f"- Agent: {agent_used}{fallback_note}\n"
        f"- Input: {skill_input or '(none)'}\n"
        f"- Output: {response_text[:500]}\n"
    )
    write_file(path / "learnings.md", existing + new_entry)

    # Persist full output to the artifact library (system of record)
    artifact_id = None
    if run_result["agent"]:
        try:
            topic = (req.topic if req else "") or ""
            artifact = save_artifact(
                skill=name, agent=agent_used, content=response_text,
                title=f"{name}: {topic}" if topic else "",
                source_topic=topic,
            )
            artifact_id = artifact["id"]
        except Exception:
            log.warning("Failed to save artifact for skill run %s", run_id, exc_info=True)

    # Log execution
    append_audit({
        "action": "skill_run",
        "skill": name,
        "agent": agent_used,
        "requested": agent_choice,
        "fallback_used": run_result["fallback_used"],
        "run_id": run_id,
        "artifact_id": artifact_id,
        "output_preview": response_text[:100],
    })

    return {
        "status": "completed" if run_result["agent"] else "failed",
        "run_id": run_id,
        "skill": name,
        "agent": agent_used,
        "requested_agent": agent_choice,
        "attempts": run_result["attempts"],
        "fallback_used": run_result["fallback_used"],
        "artifact_id": artifact_id,
        "output": response_text,
        "message": f"Skill '{name}' {'completed via ' + agent_used if run_result['agent'] else 'failed on all agents'}",
    }

@app.get("/api/skills/{name}/eval")
def get_skill_eval(name: str):
    if ".." in name or "/" in name:
        raise HTTPException(400, "Invalid skill name")
    path = BASE_DIR / "skills" / name / "score-history.json"
    if not path.exists():
        return {"scores": []}
    return {"scores": json.loads(path.read_text(encoding="utf-8"))}

# ─── Routes: Scheduler ────────────────────────────────────────────

@app.get("/api/scheduler/jobs")
def list_jobs():
    jobs_dir = BASE_DIR / "scheduler" / "jobs"
    jobs = []
    for f in sorted(jobs_dir.glob("*.json")):
        jobs.append(json.loads(f.read_text(encoding="utf-8")))
    return jobs

@app.post("/api/scheduler/jobs")
def create_job(job: ScheduleJobRequest):
    jobs_dir = BASE_DIR / "scheduler" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_data = {
        "id": str(uuid.uuid4())[:8],
        "name": job.name,
        "skill": job.skill,
        "cron": job.cron,
        "enabled": job.enabled,
        "created": get_timestamp(),
        "last_run": None,
        "next_run": None,
    }
    (jobs_dir / f"{job.name.replace(' ', '_')}.json").write_text(
        json.dumps(job_data, indent=2), encoding="utf-8"
    )
    append_audit({"action": "job_created", "job": job.name})
    return job_data

@app.delete("/api/scheduler/jobs/{job_id}")
def delete_job(job_id: str):
    jobs_dir = BASE_DIR / "scheduler" / "jobs"
    for f in jobs_dir.glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("id") == job_id:
            f.unlink()
            append_audit({"action": "job_deleted", "job_id": job_id})
            return {"status": "deleted"}
    raise HTTPException(404, "Job not found")

# ─── Routes: Audit ────────────────────────────────────────────────

@app.get("/api/audit")
def get_audit(limit: int = Query(100, le=500)):
    audit_file = BASE_DIR / "audit" / "audit.log"
    if not audit_file.exists():
        return {"entries": []}
    lines = audit_file.read_text(encoding="utf-8").strip().split("\n")
    entries = [json.loads(l) for l in lines if l.strip()]
    return {"entries": entries[-limit:]}

# ─── Routes: Cost Analytics ───────────────────────────────────────

@app.get("/api/cost")
def get_cost():
    cost_file = BASE_DIR / "data" / "cost-history.json"
    if not cost_file.exists():
        return {"entries": [], "daily_totals": {}, "monthly_projection": 0, "free_tier_alerts": []}
    return json.loads(cost_file.read_text(encoding="utf-8"))

@app.post("/api/cost/record")
def record_cost(data: dict):
    cost_file = BASE_DIR / "data" / "cost-history.json"
    cost_data = json.loads(cost_file.read_text(encoding="utf-8")) if cost_file.exists() else \
        {"entries": [], "daily_totals": {}, "monthly_projection": 0, "free_tier_alerts": []}
    cost_data["entries"].append({
        "timestamp": get_timestamp(),
        "agent": data.get("agent", "unknown"),
        "tokens": data.get("tokens", 0),
        "cost": data.get("cost", 0.0),
        "model": data.get("model", "unknown"),
    })
    cost_file.write_text(json.dumps(cost_data, indent=2), encoding="utf-8")
    return {"status": "recorded"}

# ─── Routes: Registry/Plugins ─────────────────────────────────────

@app.get("/api/plugins")
def list_plugins():
    reg_file = BASE_DIR / "registry" / "plugins.json"
    if not reg_file.exists():
        return {"plugins": []}
    return json.loads(reg_file.read_text(encoding="utf-8"))

@app.post("/api/plugins/install")
def install_plugin(data: dict):
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Plugin name required")
    reg_file = BASE_DIR / "registry" / "plugins.json"
    reg = json.loads(reg_file.read_text(encoding="utf-8")) if reg_file.exists() else {"plugins": []}
    if any(p["name"] == name for p in reg["plugins"]):
        return {"status": "already_installed"}
    reg["plugins"].append({
        "name": name,
        "installed": get_timestamp(),
        "version": "1.0.0",
    })
    reg_file.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    append_audit({"action": "plugin_installed", "plugin": name})
    return {"status": "installed", "plugin": name}

# ─── Routes: Backup ───────────────────────────────────────────────

@app.get("/api/backups")
def list_backups():
    backup_dir = BASE_DIR / "backups"
    backups = []
    for f in sorted(backup_dir.glob("*.tar.gz"), reverse=True):
        backups.append({
            "name": f.name,
            "size": f.stat().st_size,
            "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return backups

@app.post("/api/backup")
def create_backup():
    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"agentic-os-{ts}.tar.gz"
    with tarfile.open(backup_file, "w:gz") as tar:
        for dir_name in ["brain", "skills", "agents", "registry", "standards", "prompts"]:
            d = BASE_DIR / dir_name
            if d.exists():
                tar.add(d, arcname=dir_name)
    append_audit({"action": "backup_created", "file": backup_file.name})
    return {"status": "ok", "file": backup_file.name, "size": backup_file.stat().st_size}

@app.post("/api/backup/restore")
def restore_backup(data: BackupRestoreRequest):
    if ".." in data.file or "/" in data.file:
        raise HTTPException(400, "Invalid backup file")
    backup_file = BASE_DIR / "backups" / data.file
    if not backup_file.exists():
        raise HTTPException(404, "Backup file not found")
    with tarfile.open(backup_file, "r:gz") as tar:
        safe_extractall(tar, BASE_DIR)
    append_audit({"action": "backup_restored", "file": data.file})
    return {"status": "restored"}

# ─── Routes: Prompts ──────────────────────────────────────────────

@app.get("/api/prompts")
def list_prompts():
    prompts_dir = BASE_DIR / "prompts"
    prompts = {}
    for f in sorted(prompts_dir.glob("*.md")):
        prompts[f.stem] = read_file(f)
    return prompts

# ─── Routes: Settings ─────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    sf = BASE_DIR / "data" / "settings.json"
    if not sf.exists():
        return {}
    data = json.loads(sf.read_text(encoding="utf-8"))
    # Mask sensitive values
    if "api_keys" in data:
        data["api_keys"] = {k: v[:4] + "****" if len(v) > 8 else "****" for k, v in data["api_keys"].items()}
    return data

@app.put("/api/settings")
def update_settings(data: SettingsUpdate):
    sf = BASE_DIR / "data" / "settings.json"
    # Merge with existing
    existing = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else {}
    existing.update(data.settings)
    sf.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    append_audit({"action": "settings_updated"})
    return {"status": "ok"}

# ─── Routes: Webhooks & Scheduler Events (v0.3.0) ─────────────────

@app.post("/api/webhook")
def webhook_receiver(data: dict):
    """Generic webhook receiver — triggers skill execution by event type."""
    event_type = data.get("event", data.get("type", "unknown"))
    skill_name = data.get("skill", "")
    payload = data.get("payload", {})
    if skill_name:
        from scheduler.scheduler import run_skill
        result = run_skill(skill_name, trigger=f"webhook:{event_type}", input_text=json.dumps(payload))
        append_audit({"action": "webhook_received", "event": event_type, "skill": skill_name})
        return {"status": "processed", "event": event_type, "skill": skill_name, "result": result}
    append_audit({"action": "webhook_received", "event": event_type})
    return {"status": "received", "event": event_type}

@app.get("/api/scheduler/events")
def get_scheduler_events(limit: int = Query(50, le=200)):
    from scheduler.scheduler import get_history
    return {"events": get_history(limit=limit)}

@app.post("/api/scheduler/trigger/{job_id}")
def trigger_job(job_id: str):
    from scheduler.scheduler import get_job_by_id, run_skill
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    result = run_skill(job["skill"], trigger="manual")
    append_audit({"action": "job_triggered", "job_id": job_id, "skill": job["skill"]})
    return result

@app.post("/api/webhook/generic")
def generic_webhook(data: dict):
    """Catch-all webhook receiver for external tool integrations."""
    source = data.get("source", "unknown")
    event = data.get("event", data.get("action", "trigger"))
    skill = data.get("skill", "")
    if skill:
        from scheduler.scheduler import run_skill
        run_skill(skill, trigger=f"webhook:{source}:{event}")
        append_audit({"action": "generic_webhook", "source": source, "event": event, "skill": skill})
    return {"status": "ok", "source": source, "event": event}

# ─── Routes: Memory Search & Auto-Skill Generator (v0.3.0) ─────────

@app.get("/api/memory/search")
def memory_search(q: str = Query(""), limit: int = Query(20, le=100)):
    from brain.memory_search import search, extract_entities
    results = search(q, limit) if q else []
    entities = extract_entities(q) if q else []
    return {"results": results, "entities": entities, "query": q}

@app.post("/api/memory/reindex")
def memory_reindex():
    from brain.memory_search import reindex_all
    reindex_all()
    append_audit({"action": "memory_reindexed"})
    return {"status": "reindexed"}

@app.get("/api/memory/entities")
def list_entities(entity_type: str = "", limit: int = Query(50, le=200)):
    from brain.memory_search import get_entities
    return {"entities": get_entities(entity_type=entity_type, limit=limit)}

@app.post("/api/skills/generate")
def generate_skill(data: dict):
    """Auto-generate a SKILL.md from a natural language description."""
    name = data.get("name", "").strip().lower().replace(" ", "-")
    description = data.get("description", "").strip()
    if not name or not description:
        raise HTTPException(400, "Both 'name' and 'description' are required")
    if not re.match(r'^[a-z0-9-]+$', name):
        raise HTTPException(400, "Skill name must be alphanumeric with hyphens")
    skill_dir = BASE_DIR / "skills" / name
    if skill_dir.exists():
        raise HTTPException(409, "Skill already exists")
    skill_dir.mkdir(parents=True)
    (skill_dir / "context").mkdir(exist_ok=True)
    skill_md = f"""# {description}

{description}

## Usage
Generate this skill by running it with appropriate input.

## Input
- Natural language description of what to do

## Output
- Executed task result

## Primary: opencode
"""
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    (skill_dir / "learnings.md").write_text(f"# {name}\n\nAuto-generated skill.\n", encoding="utf-8")
    eval_data = {"criteria": ["completeness", "accuracy", "efficiency"], "weights": [0.4, 0.3, 0.3]}
    (skill_dir / "eval.json").write_text(json.dumps(eval_data, indent=2), encoding="utf-8")
    (skill_dir / "score-history.json").write_text("[]", encoding="utf-8")
    append_audit({"action": "skill_generated", "name": name, "description": description})
    return {"status": "created", "name": name, "skill": skill_md}

# ─── Routes: Error Tracking (v0.3.0) ───────────────────────────────

ERROR_LOG_FILE = BASE_DIR / "data" / "error-log.json"

def log_error(source: str, message: str, category: str = "general", details: dict = None):
    errors = []
    if ERROR_LOG_FILE.exists():
        errors = json.loads(ERROR_LOG_FILE.read_text(encoding="utf-8"))
    errors.append({
        "id": str(uuid.uuid4())[:8],
        "source": source,
        "message": message,
        "category": category,
        "details": details or {},
        "timestamp": get_timestamp(),
    })
    if len(errors) > 500:
        errors = errors[-500:]
    ERROR_LOG_FILE.write_text(json.dumps(errors, indent=2), encoding="utf-8")

@app.get("/api/errors")
def get_errors(limit: int = Query(50, le=200), category: str = ""):
    if not ERROR_LOG_FILE.exists():
        return {"errors": []}
    errors = json.loads(ERROR_LOG_FILE.read_text(encoding="utf-8"))
    if category:
        errors = [e for e in errors if e.get("category") == category]
    return {"errors": errors[-limit:]}

@app.delete("/api/errors")
def clear_errors():
    if ERROR_LOG_FILE.exists():
        ERROR_LOG_FILE.write_text("[]", encoding="utf-8")
    return {"status": "cleared"}

@app.post("/api/errors/report")
def report_error(data: dict):
    log_error(
        source=data.get("source", "unknown"),
        message=data.get("message", ""),
        category=data.get("category", "general"),
        details=data.get("details"),
    )
    return {"status": "reported"}

# ─── Circuit Breaker (v0.3.0) ──────────────────────────────────────

CIRCUIT_BREAKER_FILE = BASE_DIR / "data" / "circuit-breaker.json"

def _get_circuit_state() -> dict:
    if CIRCUIT_BREAKER_FILE.exists():
        return json.loads(CIRCUIT_BREAKER_FILE.read_text(encoding="utf-8"))
    return {"agents": {}, "threshold": 3, "recovery_timeout": 300}

def _save_circuit_state(state: dict):
    CIRCUIT_BREAKER_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

@app.get("/api/circuit-breaker")
def get_circuit_breaker():
    state = _get_circuit_state()
    now = time.time()
    for agent, cb in state.get("agents", {}).items():
        if cb.get("state") == "open" and now - cb.get("opened_at", 0) > state.get("recovery_timeout", 300):
            cb["state"] = "half-open"
    return state

@app.post("/api/circuit-breaker/trip")
def trip_circuit_breaker(data: dict):
    agent = data.get("agent", "")
    if agent not in KNOWN_AGENTS:
        raise HTTPException(400, "Invalid agent")
    state = _get_circuit_state()
    if agent not in state["agents"]:
        state["agents"][agent] = {"state": "closed", "failures": 0, "opened_at": None}
    cb = state["agents"][agent]
    cb["failures"] = cb.get("failures", 0) + 1
    if cb["failures"] >= state["threshold"]:
        cb["state"] = "open"
        cb["opened_at"] = time.time()
    _save_circuit_state(state)
    append_audit({"action": "circuit_tripped", "agent": agent, "failures": cb["failures"]})
    return {"agent": agent, "state": cb["state"], "failures": cb["failures"]}

@app.post("/api/circuit-breaker/reset")
def reset_circuit_breaker(data: dict):
    agent = data.get("agent", "")
    if agent not in KNOWN_AGENTS:
        raise HTTPException(400, "Invalid agent")
    state = _get_circuit_state()
    state["agents"][agent] = {"state": "closed", "failures": 0, "opened_at": None}
    _save_circuit_state(state)
    return {"agent": agent, "state": "closed"}

# ─── Routes: Standards ────────────────────────────────────────────

@app.get("/api/standards")
def list_standards():
    std_dir = BASE_DIR / "standards"
    if not std_dir.exists():
        return {"standards": []}
    standards = []
    index_file = std_dir / "index.yml"
    index_content = read_file(index_file)
    for f in std_dir.glob("*.md"):
        standards.append({
            "name": f.stem,
            "content": read_file(f),
        })
    return {"standards": standards, "index": index_content}

@app.post("/api/standards/discover")
def discover_standards():
    # Stub: scans codebase for patterns
    append_audit({"action": "standards_discovery_run"})
    return {"status": "discovery_started", "message": "Scanning codebase for patterns..."}

# ─── Routes: Chat ─────────────────────────────────────────────────

CHAT_HISTORY_FILE = BASE_DIR / "data" / "chat-history.json"

def load_chat_history():
    if not CHAT_HISTORY_FILE.exists():
        return {"messages": []}
    try:
        data = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "messages" in data:
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return {"messages": []}

def save_chat_message(msg: dict):
    history = load_chat_history()
    history.setdefault("messages", []).append(msg)
    if len(history["messages"]) > 200:
        history["messages"] = history["messages"][-200:]
    CHAT_HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")

def run_cli(args: list, timeout: int = 30) -> tuple:
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr

def clean_hermes_output(raw: str) -> str:
    """Strip CLI metadata from Hermes output, returning only the AI response."""
    if not raw:
        return ""
    lines = raw.split('\n')
    in_box = False
    content_lines = []
    for line in lines:
        if '╭─' in line:
            in_box = True
            continue
        if '╰─' in line:
            in_box = False
            continue
        if in_box:
            # Remove ANSI escape codes and leading whitespace
            cleaned = line.strip()
            if cleaned:
                content_lines.append(cleaned)
    if content_lines:
        return '\n'.join(content_lines)
    # Fallback: if no box found, return last non-metadata line
    non_meta = [l.strip() for l in lines if l.strip() and not l.startswith(('Query:', 'Initializing', '──', 'Resume', 'Session:', 'Duration:', 'Messages:'))]
    return '\n'.join(non_meta[-5:]) or raw

def execute_agent(agent: str, message: str) -> str:
    try:
        if agent == "opencode":
            try:
                code, out, err = run_cli(["opencode", "run", "--format", "json", message], timeout=30)
            except subprocess.TimeoutExpired:
                return f"⏱ Agent 'opencode' timed out.\n\nOpenCode's model is taking too long. Try running `opencode run \"{message[:60]}\"` directly in your terminal.\n\n**Message:** {message[:100]}"
            if code == 0:
                response_text = ""
                for line in (out or "").split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("type") == "text":
                            text = event.get("part", {}).get("text", "")
                            if text:
                                response_text += text + "\n"
                    except (json.JSONDecodeError, KeyError):
                        continue
                if response_text:
                    return response_text.strip()
                return f"**opencode**\n\nProcessed your message.\n\n**Message:** {message[:100]}"
            err_msg = (err or "").strip()
            return err_msg or f"opencode returned exit code {code}"

        elif agent == "hermes":
            try:
                code, out, err = run_cli(["hermes", "chat", "-q", message], timeout=180)
            except subprocess.TimeoutExpired:
                return f"⏱ Hermes timed out.\n\nThe model took too long to respond. Try a shorter query or check your OpenRouter rate limits.\n\n**Message:** {message[:100]}"
            if code == 0:
                cleaned = clean_hermes_output(out or "")
                if cleaned:
                    return cleaned
                # Empty response from model - return useful fallback
                return f"**Hermes**\n\nReceived your message but the model returned an empty response. Try rephrasing your query.\n\n**Message:** {message}"
            err_msg = (err or "").strip()
            if "invalid choice" in err_msg or "usage:" in err_msg:
                return f"**Hermes needs setup**\n\nRun `hermes setup` or check your config.\n\n**Details:** {err_msg[:200]}"
            return err_msg or f"hermes returned exit code {code}"

        elif agent == "gemini":
            for attempt, (args, to) in enumerate([
                (["-y", "-m", "gemini-2.5-flash"], 30),
                (["-y"], 30),
            ]):
                try:
                    code, out, err = run_cli(["gemini", *args, message], timeout=to)
                except subprocess.TimeoutExpired:
                    if attempt == 0:
                        continue
                    return f"**Gemini CLI timed out.**\n\nTry running `gemini \"{message[:60]}\"` directly."
                combined = ((err or "") + " " + (out or "")).strip()
                if code == 0:
                    return (out or "").strip() or f"**Gemini CLI**\n\nProcessed your query.\n\n**Message:** {message}"
                if attempt == 0 and ("model" in combined.lower() or "not found" in combined.lower()):
                    continue
                if "auth" in combined.lower() or "login" in combined.lower() or "Please set an Auth" in combined:
                    return f"**Gemini needs auth**\n\nRun `gemini auth login` to authenticate.\n\n**Details:** {combined[:200]}"
                return combined or f"gemini returned exit code {code}"
            return "Gemini CLI did not return a response."

        elif agent == "claude":
            cfg = load_agent_config("claude")
            cmd = ["claude", "-p", message, "--output-format", "json",
                   "--max-turns", str(cfg.get("max_turns", 5))]
            if cfg.get("model"):
                cmd += ["--model", cfg["model"]]
            try:
                code, out, err = run_cli(cmd, timeout=cfg.get("timeout", 180))
            except subprocess.TimeoutExpired:
                return "⏱ Claude Code timed out.\n\nTry a shorter prompt, or raise `timeout` in agents/claude/claude.json."
            if code == 0:
                try:
                    result_data = json.loads(out or "{}")
                except json.JSONDecodeError:
                    return (out or "").strip() or "Claude Code returned no output."
                cost = result_data.get("total_cost_usd")
                if cost:
                    usage = result_data.get("usage", {}) or {}
                    tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    try:
                        record_cost({"agent": "claude", "tokens": tokens,
                                     "cost": cost, "model": cfg.get("model") or "claude-default"})
                    except Exception:
                        log.warning("Failed to record claude cost", exc_info=True)
                text = (result_data.get("result") or "").strip()
                return text or "Claude Code returned an empty response."
            err_msg = (err or "").strip()
            low = err_msg.lower()
            if "log in" in low or "login" in low or "api key" in low or "authent" in low:
                return f"**Claude Code needs auth**\n\nRun `claude` once in a terminal to log in.\n\n**Details:** {err_msg[:200]}"
            return err_msg or f"claude returned exit code {code}"

        else:
            return f"Unknown agent: {agent}"
    except subprocess.TimeoutExpired:
        return f"⏱ Agent '{agent}' timed out.\n\nRun `{agent} --help` in your terminal for CLI usage.\n\n**Message:** {message[:100]}"
    except FileNotFoundError:
        return f"⚠ Agent '{agent}' CLI not installed. Install it and try again."
    except Exception as e:
        return f"⚠ Error communicating with {agent}: {str(e)}"

# ─── Artifact Library ─────────────────────────────────────────────
# Every successful skill run persists its full output here — the
# system of record, replacing the lossy 500-char learnings preview.

ARTIFACTS_DIR = BASE_DIR / "data" / "artifacts"
_ARTIFACT_ID_RE = re.compile(r"^[0-9a-f]{8}$")

class ArtifactUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[list] = None
    bookmarked: Optional[bool] = None

def save_artifact(skill: str, agent: str, content: str, title: str = "",
                  artifact_type: str = "markdown", source_topic: str = "",
                  tags: Optional[list] = None) -> dict:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    art_id = str(uuid.uuid4())[:8]
    ext = {"markdown": "md", "text": "txt"}.get(artifact_type, "txt")
    content_file = f"{art_id}.{ext}"
    (ARTIFACTS_DIR / content_file).write_text(content, encoding="utf-8")
    meta = {
        "id": art_id,
        "title": title or f"{skill} — {get_timestamp()[:10]}",
        "skill": skill,
        "agent": agent,
        "type": artifact_type,
        "tags": tags or [],
        "bookmarked": False,
        "source_topic": source_topic,
        "content_file": content_file,
        "created": get_timestamp(),
        "size": len(content),
    }
    (ARTIFACTS_DIR / f"{art_id}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    try:
        from brain.memory_search import index_text
        index_text("artifact", f"data/artifacts/{content_file}", meta["title"], content, "artifact")
    except Exception:
        log.debug("artifact FTS indexing unavailable", exc_info=True)
    return meta

def _artifact_meta_path(art_id: str) -> Path:
    if not _ARTIFACT_ID_RE.match(art_id or ""):
        raise HTTPException(400, "Invalid artifact id")
    p = ARTIFACTS_DIR / f"{art_id}.meta.json"
    if not p.exists():
        raise HTTPException(404, "Artifact not found")
    return p

def _artifact_content(meta: dict) -> str:
    f = ARTIFACTS_DIR / meta.get("content_file", "")
    return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""

@app.get("/api/artifacts")
def list_artifacts(skill: str = "", tag: str = "", bookmarked: Optional[bool] = None,
                   q: str = "", limit: int = Query(50, le=200)):
    if not ARTIFACTS_DIR.exists():
        return {"artifacts": [], "total": 0}
    items = []
    for meta_file in sorted(ARTIFACTS_DIR.glob("*.meta.json"), reverse=True):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if skill and meta.get("skill") != skill:
            continue
        if tag and tag not in meta.get("tags", []):
            continue
        if bookmarked is not None and bool(meta.get("bookmarked")) != bookmarked:
            continue
        content = _artifact_content(meta)
        if q and q.lower() not in (meta.get("title", "") + " " + content).lower():
            continue
        meta["preview"] = content[:200]
        items.append(meta)
        if len(items) >= limit:
            break
    return {"artifacts": items, "total": len(items)}

@app.get("/api/artifacts/{art_id}")
def get_artifact(art_id: str):
    meta = json.loads(_artifact_meta_path(art_id).read_text(encoding="utf-8"))
    meta["content"] = _artifact_content(meta)
    return meta

@app.patch("/api/artifacts/{art_id}")
def update_artifact(art_id: str, data: ArtifactUpdate):
    p = _artifact_meta_path(art_id)
    meta = json.loads(p.read_text(encoding="utf-8"))
    for field in ("title", "tags", "bookmarked"):
        val = getattr(data, field)
        if val is not None:
            meta[field] = val
    p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    append_audit({"action": "artifact_updated", "id": art_id})
    return meta

@app.delete("/api/artifacts/{art_id}")
def delete_artifact(art_id: str):
    p = _artifact_meta_path(art_id)
    meta = json.loads(p.read_text(encoding="utf-8"))
    content_file = ARTIFACTS_DIR / meta.get("content_file", "")
    if content_file.is_file():
        content_file.unlink()
    p.unlink()
    append_audit({"action": "artifact_deleted", "id": art_id})
    return {"status": "deleted", "id": art_id}

# ─── Fallback Chain Engine ────────────────────────────────────────
# execute_agent() reports failures as human-readable strings (v0.3.0
# style) rather than raising, so the chain engine detects them by the
# markers those strings always carry.

def _response_indicates_failure(text: str) -> bool:
    if not text:
        return True
    if text.startswith(("⏱", "⚠")):
        return True
    low = text.lower()
    return ("returned exit code" in low or "needs auth" in low
            or "needs setup" in low or "cli not installed" in low
            or "did not return a response" in low
            or low.startswith("unknown agent"))

def _paid_agents() -> set:
    return {a for a in KNOWN_AGENTS if load_agent_config(a).get("cost_tier") == "paid"}

def _circuit_open_agents() -> set:
    state = _get_circuit_state()
    now = time.time()
    out = set()
    for agent, cb in state.get("agents", {}).items():
        if cb.get("state") == "open" and now - (cb.get("opened_at") or 0) <= state.get("recovery_timeout", 300):
            out.add(agent)
    return out

def _record_agent_failure(agent: str):
    state = _get_circuit_state()
    cb = state["agents"].setdefault(agent, {"state": "closed", "failures": 0, "opened_at": None})
    cb["failures"] = cb.get("failures", 0) + 1
    if cb["failures"] >= state.get("threshold", 3):
        cb["state"] = "open"
        cb["opened_at"] = time.time()
    _save_circuit_state(state)

def _record_agent_success(agent: str):
    state = _get_circuit_state()
    state["agents"][agent] = {"state": "closed", "failures": 0, "opened_at": None}
    _save_circuit_state(state)

def _suggest_agent(task: str) -> str:
    task_lower = (task or "").lower()
    scores = {a: sum(1 for k in kws if k in task_lower) for a, kws in ROUTER_RULES.items()}
    return max(scores, key=scores.get)

def resolve_agent_chain(requested: str = "auto", primary: str = "") -> list:
    """Ordered agents to try: explicit/primary first, then fallbacks.

    Fallbacks are ordered by routing.prefer (cost|quality), with
    open-circuit and offline agents pushed to the back. routing.free_only
    removes paid backends entirely.
    """
    routing = load_settings().get("routing", {})
    if routing.get("prefer") == "quality":
        base = ["claude", "opencode", "gemini", "hermes"]
    else:
        base = ["opencode", "gemini", "hermes", "claude"]
    chain = []
    if requested and requested != "auto":
        chain.append(requested)
    elif primary:
        chain.append(primary)
    for a in base:
        if a not in chain:
            chain.append(a)
    if routing.get("free_only"):
        paid = _paid_agents()
        chain = [a for a in chain if a not in paid]
    head, rest = chain[:1], chain[1:]
    open_circuits = _circuit_open_agents()
    rest.sort(key=lambda a: (a in open_circuits, check_agent(a)["status"] != "online"))
    return head + rest

def execute_with_fallback(chain: list, message: str) -> dict:
    """Try each agent in order until one succeeds; record every attempt."""
    attempts = []
    for agent in chain:
        text = execute_agent(agent, message)
        if _response_indicates_failure(text):
            attempts.append({"agent": agent, "ok": False, "error": (text or "")[:200]})
            _record_agent_failure(agent)
            continue
        attempts.append({"agent": agent, "ok": True})
        _record_agent_success(agent)
        if len(attempts) > 1:
            append_audit({"action": "agent_fallback", "requested": chain[0],
                          "used": agent, "attempts": len(attempts)})
        return {"agent": agent, "output": text, "attempts": attempts,
                "fallback_used": len(attempts) > 1}
    summary = "⚠ All agents failed.\n\n" + "\n".join(
        f"- **{a['agent']}**: {a['error']}" for a in attempts)
    log_error("fallback", f"All {len(attempts)} agents failed", category="agent",
              details={"attempts": attempts})
    return {"agent": None, "output": summary, "attempts": attempts, "fallback_used": True}

@app.post("/api/chat")
def chat(req: ChatRequest):
    agent = req.agent.lower().strip()
    if agent != "auto" and agent not in KNOWN_AGENTS:
        raise HTTPException(400, f"Agent must be 'auto' or one of: {', '.join(KNOWN_AGENTS)}")
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(400, "Message cannot be empty")
    if len(message) > 10000:
        raise HTTPException(400, "Message too long (max 10000 characters)")

    user_msg = {
        "id": str(uuid.uuid4())[:8],
        "role": "user",
        "agent": agent,
        "content": message,
        "timestamp": get_timestamp(),
    }
    save_chat_message(user_msg)

    chain = resolve_agent_chain(agent, primary=_suggest_agent(message) if agent == "auto" else "")
    result = execute_with_fallback(chain, message)
    agent_used = result["agent"] or chain[0]

    agent_msg = {
        "id": str(uuid.uuid4())[:8],
        "role": "assistant",
        "agent": agent_used,
        "content": result["output"],
        "timestamp": get_timestamp(),
    }
    save_chat_message(agent_msg)

    append_audit({"action": "chat_message", "agent": agent_used,
                  "requested": agent, "msg_preview": message[:50]})

    return {"status": "ok", "response": agent_msg,
            "attempts": result["attempts"], "fallback_used": result["fallback_used"]}

@app.get("/api/chat/history")
def get_chat_history():
    return load_chat_history()

# ═══════════════════════════════════════════════════════════════════
# v0.2.0 — New Feature Endpoints
# ═══════════════════════════════════════════════════════════════════

# ─── Models ─────────────────────────────────────────────────────

class KanbanTaskCreate(BaseModel):
    title: str
    body: str = ""
    status: str = "triage"
    priority: str = "medium"
    assignee: str = ""

class KanbanTaskUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None

class KanbanComplete(BaseModel):
    summary: str = ""

class KanbanBlock(BaseModel):
    reason: str = ""

class KanbanCommentCreate(BaseModel):
    message: str

class KanbanLinkCreate(BaseModel):
    parent_id: str
    child_id: str

class GoalCreate(BaseModel):
    title: str
    description: str = ""
    category: str = "general"
    target_date: str = ""

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_date: Optional[str] = None
    progress: Optional[int] = None
    status: Optional[str] = None

class JournalSave(BaseModel):
    content: str

class RouterSuggest(BaseModel):
    task: str

class RouterRoute(BaseModel):
    task: str
    agent: str

# ─── Data Helpers ───────────────────────────────────────────────

KANBAN_DIR = BASE_DIR / "data" / "kanban"
GOALS_FILE = BASE_DIR / "data" / "goals.json"
JOURNAL_DIR = BASE_DIR / "brain" / "journal"

def ensure_dir(d: Path):
    d.mkdir(parents=True, exist_ok=True)

def load_kanban_tasks():
    ensure_dir(KANBAN_DIR)
    tasks = []
    for f in sorted(KANBAN_DIR.glob("*.json")):
        tasks.append(json.loads(f.read_text(encoding="utf-8")))
    return tasks

def save_kanban_task(task: dict):
    ensure_dir(KANBAN_DIR)
    (KANBAN_DIR / f"{task['id']}.json").write_text(json.dumps(task, indent=2), encoding="utf-8")

def load_goals():
    if GOALS_FILE.exists():
        return json.loads(GOALS_FILE.read_text(encoding="utf-8"))
    return []

def save_goals(goals: list):
    GOALS_FILE.write_text(json.dumps(goals, indent=2), encoding="utf-8")

# ─── Routes: Kanban Board (13 endpoints) ────────────────────────

@app.get("/api/kanban/board")
def kanban_board(status: Optional[str] = None):
    try:
        tasks = load_kanban_tasks()
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        columns = {"triage": [], "todo": [], "ready": [], "in_progress": [], "blocked": [], "done": []}
        for t in tasks:
            s = t.get("status", "triage")
            if s in columns:
                columns[s].append(t)
        return {"columns": columns, "total": len(tasks)}
    except Exception as e:
        return {"error": str(e), "columns": {}, "total": 0}

@app.get("/api/kanban/tasks/{task_id}")
def kanban_get_task(task_id: str):
    path = KANBAN_DIR / f"{task_id}.json"
    if not path.exists():
        raise HTTPException(404, "Task not found")
    return json.loads(path.read_text(encoding="utf-8"))

@app.post("/api/kanban/tasks")
def kanban_create_task(data: KanbanTaskCreate):
    try:
        task = {
            "id": str(uuid.uuid4())[:8],
            "title": data.title,
            "body": data.body,
            "status": data.status,
            "priority": data.priority,
            "assignee": data.assignee,
            "comments": [],
            "links": [],
            "created": get_timestamp(),
            "updated": get_timestamp(),
        }
        save_kanban_task(task)
        append_audit({"action": "kanban_task_created", "title": data.title})
        return task
    except Exception as e:
        raise HTTPException(500, str(e))

@app.patch("/api/kanban/tasks/{task_id}")
def kanban_update_task(task_id: str, data: KanbanTaskUpdate):
    path = KANBAN_DIR / f"{task_id}.json"
    if not path.exists():
        raise HTTPException(404, "Task not found")
    task = json.loads(path.read_text(encoding="utf-8"))
    for field in ["title", "body", "status", "priority", "assignee"]:
        val = getattr(data, field, None)
        if val is not None:
            task[field] = val
    task["updated"] = get_timestamp()
    save_kanban_task(task)
    append_audit({"action": "kanban_task_updated", "task_id": task_id})
    return task

@app.post("/api/kanban/tasks/{task_id}/complete")
def kanban_complete_task(task_id: str, data: KanbanComplete):
    path = KANBAN_DIR / f"{task_id}.json"
    if not path.exists():
        raise HTTPException(404, "Task not found")
    task = json.loads(path.read_text(encoding="utf-8"))
    task["status"] = "done"
    task["summary"] = data.summary
    task["completed_at"] = get_timestamp()
    task["updated"] = get_timestamp()
    save_kanban_task(task)
    append_audit({"action": "kanban_task_completed", "task_id": task_id})
    return task

@app.post("/api/kanban/tasks/{task_id}/block")
def kanban_block_task(task_id: str, data: KanbanBlock):
    path = KANBAN_DIR / f"{task_id}.json"
    if not path.exists():
        raise HTTPException(404, "Task not found")
    task = json.loads(path.read_text(encoding="utf-8"))
    task["status"] = "blocked"
    task["block_reason"] = data.reason
    task["updated"] = get_timestamp()
    save_kanban_task(task)
    append_audit({"action": "kanban_task_blocked", "task_id": task_id})
    return task

@app.post("/api/kanban/tasks/{task_id}/unblock")
def kanban_unblock_task(task_id: str):
    path = KANBAN_DIR / f"{task_id}.json"
    if not path.exists():
        raise HTTPException(404, "Task not found")
    task = json.loads(path.read_text(encoding="utf-8"))
    task["status"] = "ready"
    task["block_reason"] = ""
    task["updated"] = get_timestamp()
    save_kanban_task(task)
    append_audit({"action": "kanban_task_unblocked", "task_id": task_id})
    return task

@app.post("/api/kanban/tasks/{task_id}/comments")
def kanban_add_comment(task_id: str, data: KanbanCommentCreate):
    path = KANBAN_DIR / f"{task_id}.json"
    if not path.exists():
        raise HTTPException(404, "Task not found")
    task = json.loads(path.read_text(encoding="utf-8"))
    comment = {
        "id": str(uuid.uuid4())[:8],
        "message": data.message,
        "timestamp": get_timestamp(),
    }
    task.setdefault("comments", []).append(comment)
    task["updated"] = get_timestamp()
    save_kanban_task(task)
    return task

@app.post("/api/kanban/links")
def kanban_add_link(data: KanbanLinkCreate):
    for tid in [data.parent_id, data.child_id]:
        path = KANBAN_DIR / f"{tid}.json"
        if not path.exists():
            raise HTTPException(404, f"Task {tid} not found")
        t = json.loads(path.read_text(encoding="utf-8"))
        t.setdefault("links", [])
        link = {"parent": data.parent_id, "child": data.child_id}
        if link not in t["links"]:
            t["links"].append(link)
        t["updated"] = get_timestamp()
        save_kanban_task(t)
    append_audit({"action": "kanban_link_added", "parent": data.parent_id, "child": data.child_id})
    return {"status": "linked"}

@app.delete("/api/kanban/links")
def kanban_remove_link(parent_id: str = Query(...), child_id: str = Query(...)):
    for tid in [parent_id, child_id]:
        path = KANBAN_DIR / f"{tid}.json"
        if path.exists():
            t = json.loads(path.read_text(encoding="utf-8"))
            t.setdefault("links", [])
            t["links"] = [l for l in t["links"] if not (l.get("parent") == parent_id and l.get("child") == child_id)]
            t["updated"] = get_timestamp()
            save_kanban_task(t)
    return {"status": "unlinked"}

@app.post("/api/kanban/dispatch")
def kanban_dispatch():
    append_audit({"action": "kanban_dispatch_triggered"})
    return {"status": "dispatch_triggered", "message": "Dispatcher notified"}

@app.post("/api/kanban/tasks/{task_id}/specify")
def kanban_specify_task(task_id: str):
    path = KANBAN_DIR / f"{task_id}.json"
    if not path.exists():
        raise HTTPException(404, "Task not found")
    task = json.loads(path.read_text(encoding="utf-8"))
    if task.get("status") == "triage":
        task["status"] = "todo"
        task["updated"] = get_timestamp()
        save_kanban_task(task)
    return task

@app.post("/api/kanban/tasks/{task_id}/decompose")
def kanban_decompose_task(task_id: str):
    path = KANBAN_DIR / f"{task_id}.json"
    if not path.exists():
        raise HTTPException(404, "Task not found")
    task = json.loads(path.read_text(encoding="utf-8"))
    children = []
    for i, subtask in enumerate(task.get("body", "").split("\n")):
        subtask = subtask.strip().lstrip("-* ")
        if subtask:
            child = {
                "id": str(uuid.uuid4())[:8],
                "title": subtask[:80],
                "body": subtask,
                "status": "todo",
                "priority": task.get("priority", "medium"),
                "assignee": "",
                "comments": [],
                "links": [{"parent": task_id, "child": ""}],
                "created": get_timestamp(),
                "updated": get_timestamp(),
            }
            child["links"][0]["child"] = child["id"]
            save_kanban_task(child)
            children.append(child)
    return {"parent": task_id, "children": children}

# ─── Routes: Goals (4 endpoints) ─────────────────────────────────

@app.get("/api/goals")
def list_goals():
    try:
        return {"goals": load_goals()}
    except Exception as e:
        return {"goals": [], "error": str(e)}

@app.post("/api/goals")
def create_goal(data: GoalCreate):
    try:
        goals = load_goals()
        goal = {
            "id": str(uuid.uuid4())[:8],
            "title": data.title,
            "description": data.description,
            "category": data.category,
            "target_date": data.target_date,
            "status": "active",
            "progress": 0,
            "created": get_timestamp(),
            "updated": get_timestamp(),
        }
        goals.append(goal)
        save_goals(goals)
        # Auto-sync to brain/active-projects.md
        active_path = BASE_DIR / "brain" / "active-projects.md"
        if active_path.exists():
            existing = active_path.read_text(encoding="utf-8")
            existing += f"\n- [{goal['title']}](goal:{goal['id']}) — {goal['description'][:80]}\n"
            active_path.write_text(existing, encoding="utf-8")
        append_audit({"action": "goal_created", "title": data.title})
        return goal
    except Exception as e:
        raise HTTPException(500, str(e))

@app.put("/api/goals/{goal_id}")
def update_goal(goal_id: str, data: GoalUpdate):
    try:
        goals = load_goals()
        for g in goals:
            if g["id"] == goal_id:
                for field in ["title", "description", "category", "target_date", "progress", "status"]:
                    val = getattr(data, field, None)
                    if val is not None:
                        g[field] = val
                g["updated"] = get_timestamp()
                save_goals(goals)
                return g
        raise HTTPException(404, "Goal not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/goals/{goal_id}")
def delete_goal(goal_id: str):
    try:
        goals = load_goals()
        goals = [g for g in goals if g["id"] != goal_id]
        save_goals(goals)
        append_audit({"action": "goal_deleted", "goal_id": goal_id})
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(500, str(e))

# ─── Routes: Journal (4 endpoints) ───────────────────────────────

@app.get("/api/journal/entries")
def list_journal_entries():
    try:
        ensure_dir(JOURNAL_DIR)
        entries = []
        for f in sorted(JOURNAL_DIR.glob("*.md"), reverse=True):
            entries.append({
                "date": f.stem,
                "preview": f.read_text(encoding="utf-8")[:200],
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        return {"entries": entries}
    except Exception as e:
        return {"entries": [], "error": str(e)}

@app.get("/api/journal/entries/{entry_date}")
def get_journal_entry(entry_date: str):
    try:
        path = JOURNAL_DIR / f"{entry_date}.md"
        ensure_dir(JOURNAL_DIR)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        return {"date": entry_date, "content": content}
    except Exception as e:
        return {"date": entry_date, "content": "", "error": str(e)}

@app.put("/api/journal/entries/{entry_date}")
def save_journal_entry(entry_date: str, data: JournalSave):
    try:
        ensure_dir(JOURNAL_DIR)
        path = JOURNAL_DIR / f"{entry_date}.md"
        path.write_text(data.content, encoding="utf-8")
        append_audit({"action": "journal_saved", "date": entry_date})
        return {"status": "saved", "date": entry_date}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/journal/search")
def search_journal(q: str = Query("")):
    try:
        ensure_dir(JOURNAL_DIR)
        if not q:
            return {"results": []}
        results = []
        for f in JOURNAL_DIR.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            if q.lower() in content.lower():
                results.append({"date": f.stem, "preview": content[:200]})
        return {"results": results, "query": q}
    except Exception as e:
        return {"results": [], "error": str(e)}

# ─── Routes: Agent Health (3 endpoints) ──────────────────────────

@app.get("/api/agents/health")
def get_agent_health():
    try:
        agents = []
        for name in KNOWN_AGENTS:
            info = check_agent(name)
            info["uptime"] = 0
            info["success_rate"] = 100
            info["last_seen"] = get_timestamp()
            agents.append(info)
        return {"agents": agents, "updated": get_timestamp()}
    except Exception as e:
        return {"agents": [], "error": str(e), "updated": get_timestamp()}

@app.get("/api/agents/{name}/stats")
def get_agent_stats(name: str):
    try:
        if name not in KNOWN_AGENTS:
            raise HTTPException(400, "Invalid agent")
        info = check_agent(name)
        return {
            "name": name,
            "status": info["status"],
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "avg_response_time": 0,
            "last_seen": get_timestamp(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/agents/health/refresh")
def refresh_agent_health():
    try:
        agents = []
        for name in KNOWN_AGENTS:
            info = check_agent(name)
            agents.append(info)
        append_audit({"action": "agent_health_refreshed"})
        return {"agents": agents, "updated": get_timestamp()}
    except Exception as e:
        return {"agents": [], "error": str(e)}

# ─── Routes: Smart Router (2 endpoints) ─────────────────────────

ROUTER_RULES = {
    "opencode": ["code", "devops", "deploy", "git", "file", "terraform", "docker", "test", "build", "infra", "script"],
    "hermes": ["memory", "schedule", "channel", "skill", "cron", "reminder", "brain", "plugin", "backup"],
    "gemini": ["research", "analyze", "search", "compare", "explain", "study", "learn", "document", "report", "review"],
    "claude": ["implement", "refactor", "architect", "orchestrate", "spec", "prd", "pipeline", "complex", "multi-step", "feature"],
}

@app.post("/api/router/suggest")
def router_suggest(data: RouterSuggest):
    try:
        task_lower = data.task.lower()
        scores = {}
        for agent, keywords in ROUTER_RULES.items():
            scores[agent] = sum(1 for k in keywords if k in task_lower)
        best = max(scores, key=scores.get)
        confidence = "high" if scores[best] >= 2 else "medium" if scores[best] == 1 else "low"
        return {
            "suggested_agent": best,
            "confidence": confidence,
            "scores": scores,
            "task": data.task,
        }
    except Exception as e:
        return {"suggested_agent": "opencode", "confidence": "low", "error": str(e)}

@app.post("/api/router/route")
def router_route(data: RouterRoute):
    try:
        agent = data.agent.lower()
        if agent not in KNOWN_AGENTS:
            return {"status": "error", "message": f"Invalid agent: {agent}"}
        append_audit({"action": "task_routed", "agent": agent, "task_preview": data.task[:50]})
        return {
            "status": "routed",
            "agent": agent,
            "task": data.task,
            "message": f"Task routed to {agent}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── Routes: Learning Analytics (2 endpoints) ───────────────────

@app.get("/api/analytics/skills")
def get_skill_analytics():
    try:
        skills_dir = BASE_DIR / "skills"
        analytics = []
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("_"):
                eval_path = d / "eval.json"
                score_path = d / "score-history.json"
                scores = json.loads(score_path.read_text(encoding="utf-8")) if score_path.exists() else []
                eval_data = json.loads(eval_path.read_text(encoding="utf-8")) if eval_path.exists() else {}
                avg_score = sum(s.get("score", 0) for s in scores) / len(scores) if scores else 0
                analytics.append({
                    "name": d.name,
                    "total_runs": len(scores),
                    "avg_score": round(avg_score, 1),
                    "last_score": scores[-1].get("score", 0) if scores else 0,
                    "trend": "up" if len(scores) >= 2 and scores[-1].get("score", 0) > scores[-2].get("score", 0) else "down" if len(scores) >= 2 else "stable",
                })
        return {"skills": sorted(analytics, key=lambda x: x["total_runs"], reverse=True)}
    except Exception as e:
        return {"skills": [], "error": str(e)}

@app.get("/api/analytics/trends")
def get_trend_analytics():
    try:
        skills_dir = BASE_DIR / "skills"
        trends = []
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("_"):
                score_path = d / "score-history.json"
                scores = json.loads(score_path.read_text(encoding="utf-8")) if score_path.exists() else []
                if scores:
                    trends.append({
                        "name": d.name,
                        "scores": [s.get("score", 0) for s in scores[-10:]],
                        "labels": [s.get("date", "") for s in scores[-10:]],
                    })
        return {"trends": trends}
    except Exception as e:
        return {"trends": [], "error": str(e)}

# ─── Routes: Session Replay (2 endpoints) ───────────────────────

@app.get("/api/sessions/list")
def list_sessions():
    try:
        sessions = []
        sessions_dir = agent_data_dir("opencode")
        log_dir = sessions_dir / "log"
        if log_dir.exists():
            for f in sorted(log_dir.glob("*.log"), reverse=True)[:20]:
                sessions.append({
                    "id": f.stem,
                    "name": f.stem,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    "source": "opencode",
                })
        hermes_sessions = agent_data_dir("hermes") / "sessions.json"
        if hermes_sessions.exists():
            sessions.append({
                "id": "hermes-sessions",
                "name": "Hermes Session Archive",
                "size": hermes_sessions.stat().st_size,
                "modified": datetime.fromtimestamp(hermes_sessions.stat().st_mtime).isoformat(),
                "source": "hermes",
            })
        return {"sessions": sessions}
    except Exception as e:
        return {"sessions": [], "error": str(e)}

MAX_SESSION_CONTENT = 2000

@app.get("/api/sessions/{session_id}/replay")
def get_session_replay(session_id: str):
    if ".." in session_id or "/" in session_id:
        raise HTTPException(400, "Invalid session ID")
    try:
        sessions_dir = agent_data_dir("opencode")
        log_file = sessions_dir / "log" / f"{session_id}.log"
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            messages = []
            for line in lines:
                if "user:" in line.lower() or "assistant:" in line.lower():
                    messages.append(line)
            return {
                "session_id": session_id,
                "lines": len(lines),
                "messages": messages[:50],
                "content": content[:MAX_SESSION_CONTENT],
            }
        return {"session_id": session_id, "messages": [], "content": "Session log not found"}
    except Exception as e:
        return {"session_id": session_id, "messages": [], "error": str(e)}

# ─── Routes: Dashboard Static Files ──────────────────────────────

dashboard_dir = BASE_DIR / "dashboard"
if dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir)), name="dashboard")

@app.get("/", response_class=HTMLResponse)
def index():
    html_file = BASE_DIR / "dashboard" / "index.html"
    if html_file.exists():
        content = html_file.read_text(encoding="utf-8")
        content = content.replace('href="styles.css"', 'href="/dashboard/styles.css"')
        content = content.replace('src="utils.js"', 'src="/dashboard/utils.js"')
        content = content.replace('src="api.js"', 'src="/dashboard/api.js"')
        content = content.replace('src="app.js"', 'src="/dashboard/app.js"')
        content = content.replace('pages/', '/dashboard/pages/')
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>Agentic OS</h1><p>Dashboard not built yet. Run <code>./install.sh</code> first.</p>")

# ─── Favicon ──────────────────────────────────────────────────────

FAVICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#6c5ce7"/><stop offset="100%" stop-color="#fd79a8"/></linearGradient></defs><rect width="32" height="32" rx="8" fill="url(#g)"/><polygon points="16,6 24,11 24,21 16,26 8,21 8,11" fill="none" stroke="white" stroke-width="2" stroke-linejoin="round"/><circle cx="16" cy="16" r="3" fill="white"/></svg>'

@app.get("/favicon.ico")
def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@app.get("/favicon.svg")
def favicon_svg():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

# ─── PWA Support (v0.3.0) ──────────────────────────────────────────

MANIFEST_JSON = {
    "name": "Agentic OS",
    "short_name": "AgenticOS",
    "description": "Multi-agent orchestration platform",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0f0f23",
    "theme_color": "#6c5ce7",
    "icons": [
        {"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"},
    ],
}

@app.get("/manifest.json")
def manifest():
    return JSONResponse(content=MANIFEST_JSON)

SERVICE_WORKER_JS = """
self.addEventListener('install', (e) => {
  self.skipWaiting();
});
self.addEventListener('activate', (e) => {
  e.waitUntil(clients.claim());
});
self.addEventListener('fetch', (e) => {
  e.respondWith(fetch(e.request).catch(() => new Response('Offline', {status: 503})));
});
"""

@app.get("/sw.js")
def service_worker():
    return Response(content=SERVICE_WORKER_JS, media_type="application/javascript")

# ─── Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
