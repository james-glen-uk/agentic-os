# PRD V2: Agentic OS Improvements — From Linux MVP to Daily-Driver Mission Control

| | |
|---|---|
| **Status** | Draft v1.0 — approved scope |
| **Date** | 2026-07-03 |
| **Baseline** | agentic-os v0.3.0 (commit `2cdd2e6`) |
| **Inputs** | Original spec [`PRD-V1.md`](PRD-V1.md) (R1–R15), full code inventory of this repo, firsthand run/debug on Windows 11 |
| **Companion** | [`TASKS.md`](TASKS.md) — phased execution checklist |

---

## 1. Context & Problem Statement

agentic-os v0.3.0 is a genuinely strong foundation: 75 API endpoints, 21 dashboard pages, a 3-agent engine (opencode / Hermes / Gemini CLI), SQLite FTS5 memory, an event-driven scheduler, kanban, goals, cost analytics, and a circuit breaker. But as a daily driver it falls short in four ways:

1. **It doesn't run on Windows.** `install.sh` hard-rejects non-Linux/macOS; 60+ unencoded `read_text()`/`write_text()` calls crash on cp1252 (proven: HTTP 500 on first page load from `server.py:1529`); agent paths like `~/.local/share/opencode` are Linux-only. There are **zero tests** to catch any of this.
2. **The README overclaims.** Voice mode, browser automation, messaging channels, cost-aware routing, subagent delegation, and multi-provider fallback are documented but not implemented. Routing is keyword matching; fallback is a bare try/except.
3. **No content-engine loop.** The one-click trending-news → SEO article → social drafts cycle (the core value in our original PRD R5/R6) doesn't exist: no RSS ingestion, no topic clustering, no artifact library — skill outputs vanish into `learnings.md` previews.
4. **No real orchestration.** Kanban has promising `specify`/`decompose` stubs, but there is no role-based multi-agent delegation, no idea→spec→build→preview pipeline, and no premium coding backend to power builds.

This PRD upgrades the project along those four axes, adding **Claude Code as a fourth first-class agent**, while preserving what already works.

## 2. Goals

1. **Windows-native**: fresh clone → `install.ps1` → `start.ps1` → working dashboard on Windows 11 with zero manual workarounds (and Linux/macOS unchanged).
2. **Honest resilience**: every agent call runs through an ordered fallback chain that consults circuit-breaker state and agent health; a single offline CLI never fails a skill run that another agent could serve. README claims match code.
3. **Content loop in ≤ 5 minutes**: trending topic (auto-refreshed every 24h) → one-click SEO article + social drafts → saved, tagged, searchable in an artifact library.
4. **Orchestrated builds**: a goal typed into the dashboard becomes decomposed subtasks executed across 4 agents (Claude Code for build steps), visible on an org chart, producing previewable artifacts.
5. **Tested core**: every P0 endpoint covered by pytest; CI-runnable with `pytest` from a clean clone.

## 3. Non-Goals

1. **No SaaS / multi-tenant / auth** — stays single-user, localhost-first (carried from original PRD).
2. **No autonomous external publishing** — all content outputs remain human-approved drafts; auto-posting stays P2-gated behind a single publishing gateway.
3. **No model training/fine-tuning** — orchestration of existing CLIs/APIs/local models only.
4. **No frontend framework rewrite** — the vanilla-JS SPA pattern (`dashboard/pages/*.js` + `api.js`) stays; new pages follow it. A React port would burn the whole budget for zero user-visible capability.
5. **No removal of the free-tier trio** — Claude Code is added, not substituted; "free-only" mode must keep everything functional without it.

## 4. Requirements

Priorities: **P0** = this upgrade cycle cannot ship without it. **P1** = fast follow. **P2** = design for, don't build.

---

### Epic A (P0) — Platform Hardening & Windows Support

**A1. UTF-8-safe file I/O everywhere.**
Builds on: every `read_text`/`write_text`/`open` call in `server.py`, `scheduler/scheduler.py`, `brain/memory_search.py`.
- [ ] All text file I/O passes `encoding="utf-8"` explicitly (belt), and entrypoints enforce UTF-8 mode (suspenders)
- [ ] Given a fresh clone on Windows, when `GET /` is requested, then the dashboard returns 200 (regression test for the `server.py:1529` cp1252 crash)

**A2. Native Windows install & start.**
Builds on: `install.sh`, `start.sh`.
- [ ] `install.ps1` mirrors `install.sh` (dep install via `py` launcher, dir creation, CLI detection incl. `claude`); `start.ps1` mirrors `start.sh` (port from `data/settings.json`, UTF-8 mode)
- [ ] `install.sh` detects MSYS/Git-Bash (`MINGW*`/`MSYS*` in `uname -s`) and delegates or instructs instead of `exit 1`
- [ ] README Quick Start gains a Windows section

**A3. Platform-aware agent paths.**
Builds on: session/health path logic in `server.py` (`~/.local/share/opencode`, `~/.hermes/.env`, `~/.gemini/oauth_creds.json`).
- [ ] One `platform_paths` helper resolves per-OS locations for each agent's config/session dirs; all hardcoded `Path.home()/...` call sites use it
- [ ] `/api/status` and `/api/agents/health` report accurate availability on Windows

**A4. Startup validation & logging.**
- [ ] On boot, server validates each enabled agent CLI (`--version` probe with timeout), logs found/missing with install hints, and marks missing agents offline instead of failing at call time
- [ ] `print()` diagnostics replaced with the `logging` module (level configurable in `data/settings.json`)

**A5. Test suite (pytest + FastAPI TestClient).**
Builds on: none — currently zero tests.
- [ ] `tests/` with fixtures that isolate runtime data (temp `data/`, `brain/`, `skills/` dirs)
- [ ] Coverage for: index page, brain CRUD, skills list/run (agent subprocess mocked), scheduler job CRUD, kanban lifecycle, goals, journal, memory search, settings masking, backup/export, circuit breaker, fallback routing (Epic C), artifact library (Epic D)
- [ ] `pytest` passes from a clean clone on Windows and Linux; GitHub Actions workflow runs it on both

---

### Epic B (P0) — Claude Code as Fourth First-Class Agent

**B1. Claude Code backend in the agent engine.**
Builds on: `execute_agent()` (`server.py:824–895`), agent configs in `agents/`.
- [ ] New `claude` branch invoking `claude -p "<prompt>" --output-format json` (headless, non-interactive, sandboxed to a workspace dir); response text parsed from JSON
- [ ] `agents/claude/` config (role: premium coding/orchestration; model; max-turns cap) following the `agents/opencode/` pattern
- [ ] Timeout + failure feeds the existing circuit breaker (`/api/circuit-breaker`) and error log exactly like the other three agents

**B2. Full platform integration.**
Builds on: `/api/agents/health`, `/api/chat`, smart router, cost tracking (`/api/cost/record`), `data/agent-routes.json`.
- [ ] Claude appears in: agent health page, chat agent selector, smart-router suggestions, cost analytics (tokens/cost recorded per run), skill `Primary:` assignments
- [ ] Routing rules added to `data/agent-routes.json`: complex/multi-step build & orchestration keywords → claude
- [ ] Given Claude Code is not installed, when health is checked, then claude shows offline and routing never selects it (free-tier trio fully functional without it)

---

### Epic C (P0) — Real Routing & Fallback Chains

**C1. Ordered fallback chains.**
Builds on: `execute_agent()`, circuit breaker state (`data/circuit-breaker.json`), agent health checks, keyword router (`server.py:301–319`, `/api/router/suggest`).
- [ ] Each skill/chat call resolves an ordered agent list (skill config override → routes file → router suggestion → default); execution tries agents in order, skipping any with an open circuit or offline health
- [ ] Given the primary agent fails or is tripped, when a skill runs, then it completes on the next agent and the run record + audit log note the substitution
- [ ] A run fails only when every configured agent is exhausted; the error dashboard shows the full attempt chain

**C2. Free-only mode & cost-aware ordering.**
Builds on: `data/settings.json`, cost tracking.
- [ ] Global `"routing": {"free_only": true|false}` setting: when true, paid backends (claude) are excluded from all chains
- [ ] Chain ordering can prefer `cost` or `quality` (setting); per-run estimated cost recorded as today
- [ ] README routing section rewritten to match actual behavior (removes overclaim)

---

### Epic D (P0) — Content Engine: News Oracle + One-Click Workflows + Artifact Library

**D1. News Oracle.**
Builds on: event-driven scheduler (`scheduler/scheduler.py`, `scheduler/jobs/`), skill system, Gemini agent (research role).
- [ ] `news-oracle` skill: fetch configured RSS/Atom feeds (stdlib or `feedparser`; feeds listed in `data/settings.json`), then LLM-cluster into ranked trending topics; results persisted to `data/news/YYYY-MM-DD.json`
- [ ] Scheduled job `news-oracle-job.json` (daily, cron-configurable) + manual trigger via existing `/api/scheduler/trigger/{job_id}`
- [ ] `GET /api/news/topics` (+ date param) and a new dashboard page `pages/news.js`: topic cards with source links, trend rank, and per-card one-click actions
- [ ] Failed overnight run is retried and the page shows data age (never silently stale)

**D2. One-click SEO & social workflows.**
Builds on: `content-draft` skill, `skills/_template/`, prompts library.
- [ ] `seo-article` skill: topic (typed or passed from a News Oracle card) → structured long-form markdown draft; `social-drafts` skill: topic → platform-tailored post set (X + LinkedIn), linked to source topic
- [ ] Topic context (headlines, links, cluster summary) is injected automatically when triggered from a news card — zero re-prompting
- [ ] Outputs are drafts saved to the Artifact Library; nothing auto-publishes (Non-Goal 2)

**D3. Artifact Library.**
Builds on: skill run path (`/api/skills/{name}/run`), audit trail, FTS5 memory (`brain/memory_search.py`).
- [ ] Every skill run's full output auto-saved as an artifact: content file in `data/artifacts/` + metadata (skill, agent, timestamp, source topic, tags) — replaces today's lossy 500-char `learnings.md` preview as the system of record
- [ ] `GET/PATCH/DELETE /api/artifacts` endpoints: list, filter by skill/tag/bookmark, full-text search (indexed into the existing FTS5 db), bookmark toggle, tag edit
- [ ] Dashboard page `pages/artifacts.js`: grid with preview, bookmark, tags, search; library is append-only except explicit user delete

---

### Epic E (P1) — Multi-Agent Orchestration & Build Pipeline

**E1. Role-based orchestration ("zero-human company").**
Builds on: kanban `decompose` (`server.py:1182–1209`), task links, smart router, 4-agent engine.
- [ ] Role definitions in `agents/roles/*.md` (CEO=planner/arbiter, CTO=technical design, Researcher, Builder, Reviewer…), each mapping to a backend agent + persona prompt
- [ ] `POST /api/orchestrate`: goal → CEO-role decomposition into linked kanban subtasks (reuses `decompose` + `/api/kanban/links`), each assigned a role/agent; independent subtasks run concurrently; results aggregated into a final artifact
- [ ] Org-chart dashboard page showing roles, live task assignments, and statuses; every external side effect remains human-approved
- [ ] Runaway protection: max subtask depth, max total agent calls, and max spend per orchestration run (configurable)

**E2. Idea → Spec → Build → Preview pipeline.**
Builds on: kanban `specify` (`server.py:1170–1180`), Claude Code backend (B1), session replay page pattern.
- [ ] Pipeline states mapped onto kanban: idea (triage) → spec (AI-drafted via `specify`, human-editable) → build (Claude Code headless run in a sandboxed `workspace/<task-id>/` dir) → preview (rendered output / file listing / served static preview in dashboard)
- [ ] Build logs streamed/stored per task and browsable like session replay; builds cannot write outside their sandbox dir

---

### Epic F (P1) — Media Generation

**F1. Image/thumbnail workflow** (first, since Gemini CLI is already integrated).
- [ ] `image-gen` skill + provider adapter: prompt + saved style presets → image file saved to Artifact Library with metadata; graceful "provider not configured" state
**F2. Music & avatar video** behind the same adapter interface (providers configurable in settings; P1-late/P2 if API access is unavailable)
- [ ] Generated media previews (audio player / video embed / image grid) render in the artifact library page

---

### Epic G (P1) — Voice Control

**G1. Push-to-talk skill triggering.**
Builds on: dashboard SPA, smart router, skills API.
- [ ] Mic button (Web Speech API first; local Whisper adapter later) → transcript → router maps to skill + params → confirmation chip → run
- [ ] Unrecognized commands ask for confirmation instead of guessing; works in Chrome/Edge on Windows
- [ ] Removes the README's phantom "voice mode" overclaim by making it real

---

### Epic H (P1) — Save-File v2 & Backend Benchmarking

**H1. Shareable export/import ("save file").**
Builds on: `backup.sh`, `/api/backup`, `/api/backup/restore`.
- [ ] `POST /api/export`: archive of config, skills, prompts, roles, dashboard settings — **excluding** secrets (`data/settings.json` api_keys, `.env`s), runtime data, and backups
- [ ] `POST /api/import`: validates archive, lists missing dependencies (CLIs, API keys, feeds) with setup instructions, then applies; never overwrites existing secrets
**H2. Backend bench ("Goldie-bench").**
Builds on: skill eval scoring (`eval.json`, `score-history.json`), learning analytics pages.
- [ ] Bench task set runnable across all healthy agents; leaderboard page with score/latency/cost per backend; results surfaced as routing recommendations (feeds C2 ordering)

---

### P2 — Future Considerations (design-for only)

- **Encrypted API key storage** (OS keychain via `keyring`) — keep all key access behind one settings accessor now
- **Auto-generated docs site** (OpenAPI export + capability pages) — keep endpoint docstrings current
- **Approved auto-publishing** — keep all outbound content behind a single publishing gateway module
- **Standards discovery** — implement the `/api/standards/discover` stub with real pattern scanning
- **Rate limiting / CSRF** for any future non-localhost deployment

## 5. Success Metrics

**Leading (2 weeks after each phase ships)**
- Clean-clone Windows setup → working dashboard: **≤ 5 min, zero manual fixes**
- Skill-run success rate with one agent offline: **≥ 95%** (fallback saves); silent failures: **0**
- News topic → SEO article + social drafts: **≤ 5 min**, ≤ 2 clicks per output
- `pytest` suite: **green on Windows + Linux CI**, P0 endpoint coverage 100%

**Lagging (1–3 months)**
- Share of AI content work done through the dashboard vs. ad-hoc tools: **≥ 80%**
- Artifacts library becomes system of record: **100%** of skill outputs captured (vs. 500-char previews today)
- README claim audit: **0** documented-but-unimplemented features

## 6. Open Questions

| # | Question | Owner | Blocking? |
|---|----------|-------|-----------|
| 1 | Claude Code invocation limits: cap `--max-turns`/spend per orchestration run — what defaults? | Eng | Yes for E1 |
| 2 | RSS feed starter set for News Oracle (user's niches)? | User | No — ship with tech/AI defaults, editable in settings |
| 3 | `feedparser` dependency vs. stdlib XML parsing for RSS? | Eng | No — decide in D1 |
| 4 | Image provider: Gemini image API vs. local SD via ComfyUI adapter first? | User | No — adapter hides choice |
| 5 | Upstream contribution: PR Epics A–C back to modimihir07/agentic-os, or maintain a fork? | User | No — affects git workflow only |

## 7. Traceability

| V2 Epic | Original PRD | Existing code it builds on |
|---|---|---|
| A Platform/Windows | (new — firsthand findings) | `server.py`, `scheduler/scheduler.py`, `install.sh`/`start.sh` |
| B Claude Code agent | R3 (Claude Code as engine) | `execute_agent()` server.py:824–895, `agents/`, circuit breaker |
| C Routing/fallback | R3 (fallback chains), Goal 3 | keyword router server.py:301–319, `data/agent-routes.json`, circuit breaker, health |
| D Content engine | R5, R6, R8 | scheduler jobs, `content-draft` skill, FTS5 `brain/memory_search.py` |
| E Orchestration | R10, R11 | kanban `specify`/`decompose` server.py:1170–1209, task links, smart router |
| F Media generation | R6 (image), R14 | skill template, artifact library (D3) |
| G Voice | R9 | dashboard SPA, smart router |
| H Save-file + bench | R15, R13 | `/api/backup`, eval scoring, learning analytics |
| P2 set | R12, publishing gate, security | settings accessor, audit trail |
