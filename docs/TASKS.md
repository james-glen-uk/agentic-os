# TASKS — Agentic OS V2 Upgrade

Execution checklist for [`PRD-V2.md`](PRD-V2.md). Tasks are sized for one focused Claude Code session each. Work phases in order — later phases depend on earlier ones. Check off tasks as they land; every task lists its PRD requirement, the files it touches, and its done-criteria.

**Conventions**
- Baseline: v0.3.0, commit `2cdd2e6`. Branch per phase (`phase-0-hardening`, …), commit per task.
- Never break the free-tier trio: after every task, `py -3.11 -X utf8 server.py --port 8080` (or `./start.sh`) must still serve a working dashboard.
- From Phase 0 onward: `pytest` must be green before a task is checked off.

---

## Phase 0 — Platform Hardening & Windows Support (PRD Epic A) `P0`

- [x] **0.1 UTF-8-safe file I/O** *(A1)*
  Files: `server.py`, `scheduler/scheduler.py`, `brain/memory_search.py`
  Add `encoding="utf-8"` to every `read_text()`, `write_text()`, and text-mode `open()` (~60+ call sites; grep for all three patterns). Add `errors="replace"` only where reading external/agent-produced logs.
  **Done when:** `GET /` returns 200 on Windows *without* `-X utf8`; grep finds no unencoded text I/O.

- [x] **0.2 Test harness bootstrap** *(A5)*
  Files: new `tests/conftest.py`, `tests/test_smoke.py`, `requirements-dev.txt` (pytest, httpx)
  Fixtures: temp copies of `data/`, `brain/`, `skills/` so tests never touch real runtime state; FastAPI `TestClient` app factory; regression test for the 0.1 cp1252 crash (serve index containing non-ASCII bytes).
  **Done when:** `pytest` runs green from clean clone; runtime dirs untouched after test run.

- [x] **0.3 Windows install/start scripts** *(A2)*
  Files: new `install.ps1`, new `start.ps1`, edit `install.sh`, `README.md`
  `install.ps1`: `py -3.11` detection, `pip install -r requirements.txt`, create `backups/ audit/`, detect opencode/hermes/gemini/claude CLIs with install hints. `start.ps1`: read port from `data/settings.json`, launch with UTF-8 env. `install.sh`: handle `MINGW*|MSYS*` by pointing to `install.ps1` instead of `exit 1`. README gets a Windows Quick Start.
  **Done when:** fresh clone on Windows: `./install.ps1; ./start.ps1` → dashboard up.

- [x] **0.4 Platform-aware agent paths** *(A3)*
  Files: `server.py` (new `platform_paths` helper + all `Path.home()/...` call sites: opencode sessions `~/.local/share/opencode`, hermes `~/.hermes/.env`, gemini `~/.gemini/oauth_creds.json`)
  Resolve per-OS equivalents (`%LOCALAPPDATA%`/`%USERPROFILE%` on Windows); single helper, no scattered conditionals.
  **Done when:** `/api/status` and `/api/agents/health` report real availability on Windows; unit test covers path resolution per platform (monkeypatched).

- [x] **0.5 Startup validation & logging** *(A4)*
  Files: `server.py`, `scheduler/scheduler.py`, `data/settings.json` schema
  On boot: probe each enabled agent CLI (`--version`, short timeout), log found/missing + hint, cache result for health endpoints. Replace `print()` with `logging` (level from settings).
  **Done when:** boot log shows a clear agent availability table; missing CLI ⇒ agent offline, not runtime exceptions.

- [x] **0.6 P0 endpoint test coverage** *(A5)*
  Files: `tests/test_brain.py`, `test_skills.py`, `test_scheduler.py`, `test_kanban.py`, `test_goals_journal.py`, `test_settings.py`, `test_memory_search.py`, `test_backup.py`, `test_circuit_breaker.py`; new `.github/workflows/ci.yml`
  Mock `subprocess.run` for agent execution. Include security regressions (path traversal on brain/skill names, settings key masking).
  **Done when:** CI green on `windows-latest` + `ubuntu-latest`.

## Phase 1 — Claude Code Agent + Real Routing (PRD Epics B, C) `P0`

- [x] **1.1 Claude Code backend** *(B1)*
  Files: `server.py` `execute_agent()` (824–895), new `agents/claude/claude.json`
  New branch: `claude -p "<prompt>" --output-format json` headless, cwd = dedicated workspace dir, timeout + `--max-turns` cap from agent config; parse response text from JSON. Failures feed circuit breaker + error log like other agents.
  **Done when:** `POST /api/chat {"agent":"claude", ...}` returns a response with Claude Code installed; tests cover parse + timeout paths (mocked).

- [x] **1.2 Claude platform integration** *(B2)*
  Files: `server.py` (health check, router), `data/agent-routes.json`, `dashboard/pages/chat.js`, `agent-health.js`, `smart-router.js`, `cost.js` labels
  Health probe (platform-aware via 0.4), chat selector entry, routes for complex/build/orchestration keywords, cost recording per run (tokens from JSON output).
  **Done when:** claude appears in health/chat/router/cost pages; with claude absent, trio behavior is byte-for-byte unchanged (test).

- [x] **1.3 Fallback chain engine** *(C1)*
  Files: `server.py` (new `resolve_agent_chain()` + `execute_with_fallback()` wrapping `execute_agent()`), `data/agent-routes.json` (chain config)
  Order: skill `Primary:`/config override → routes file → router suggestion → default. Skip agents with open circuit (`data/circuit-breaker.json`) or offline health. Record attempt chain in run result + audit.
  **Done when:** test: primary mocked to fail ⇒ run succeeds on secondary, audit notes substitution; all agents exhausted ⇒ error dashboard shows full chain.

- [x] **1.4 Free-only mode + cost-aware ordering** *(C2)*
  Files: `server.py`, `data/settings.json` (`routing.free_only`, `routing.prefer`), `dashboard/pages/settings.js`, `README.md`
  `free_only=true` excludes claude from every chain; `prefer: cost|quality` reorders. Rewrite README routing/fallback section to match reality.
  **Done when:** toggle in settings UI works; tests cover both modes; README claim audit for routing passes.

## Phase 2 — Content Engine (PRD Epic D) `P0`

- [x] **2.1 Artifact Library backend** *(D3)* — *first: everything else saves into it*
  Files: `server.py` (new `/api/artifacts` GET/PATCH/DELETE + auto-save hook in `/api/skills/{name}/run`), new `data/artifacts/` layout (content file + `meta.json`), `brain/memory_search.py` (index artifacts into FTS5)
  **Done when:** every skill run persists full output as an artifact; list/filter/search/bookmark/tag/delete endpoints tested.

- [ ] **2.2 Artifact Library page** *(D3)*
  Files: new `dashboard/pages/artifacts.js`, `dashboard/index.html` (nav), `dashboard/api.js`, `styles.css`
  Grid with type-aware preview (markdown render, image, audio/video stubs for Phase 3), bookmark star, tag chips, search box. Follow existing page-module pattern (e.g. `journal.js`).
  **Done when:** artifacts from 2.1 browse/search/bookmark correctly in UI.

- [ ] **2.3 News Oracle skill + job** *(D1)*
  Files: new `skills/news-oracle/` (SKILL.md, eval.json, fetch+cluster logic), new `scheduler/jobs/news-oracle-job.json`, `data/settings.json` (`news.feeds` list with tech/AI defaults), `requirements.txt` (feedparser — per PRD open Q3, default choice)
  Fetch feeds → LLM topic clustering (routed via chain, research-typed ⇒ gemini primary) → `data/news/YYYY-MM-DD.json`. Daily cron + manual trigger via existing `/api/scheduler/trigger/{job_id}`. Retry on failure; stamp data age.
  **Done when:** manual trigger produces ranked topic JSON with sources; job visible/toggleable in scheduler page.

- [ ] **2.4 News page + one-click actions** *(D1, D2)*
  Files: `server.py` (new `GET /api/news/topics`), new `dashboard/pages/news.js`, nav wiring
  Topic cards: rank, headlines, source links, data-age badge, buttons **SEO article** / **Social drafts** that invoke 2.5 skills with topic context injected.
  **Done when:** click on a card button → skill runs with topic context → artifact appears in library, linked back to topic.

- [ ] **2.5 SEO article + social drafts skills** *(D2)*
  Files: new `skills/seo-article/`, new `skills/social-drafts/` (from `skills/_template/`), prompt templates in `prompts/`
  Accept topic payload (headlines/links/summary) or free-text input. Outputs saved as library drafts — no external posting.
  **Done when:** both runnable standalone from Skills Hub and from news cards; outputs are structured markdown, tested with mocked agent.

## Phase 3 — Orchestration, Media, Voice (PRD Epics E, F, G) `P1`

- [ ] **3.1 Role definitions + orchestrator API** *(E1)*
  Files: new `agents/roles/*.md` (ceo, cto, researcher, builder, reviewer), `server.py` (new `POST /api/orchestrate`), reuse kanban `decompose` (1182–1209) + `/api/kanban/links`
  Goal → CEO decomposition → linked subtasks with role/agent assignment → execution via fallback chains (builder ⇒ claude primary) → aggregated result artifact. Guardrails: max depth, max calls, max spend per run (settings).
  **Done when:** test goal produces linked kanban subtasks, runs to aggregated artifact, respects caps.

- [ ] **3.2 Org-chart page** *(E1)*
  Files: new `dashboard/pages/orchestration.js`, nav wiring
  Roles with live assignment/status, per-run drill-down into subtask outputs.
  **Done when:** an orchestration run is watchable live in the UI.

- [ ] **3.3 Idea→Spec→Build→Preview pipeline** *(E2)*
  Files: `server.py` (extend kanban `specify` 1170–1180; new build endpoint), new `workspace/` sandbox convention, `dashboard/pages/kanban.js` (pipeline actions), preview pane page
  Build = Claude Code headless in `workspace/<task-id>/` only; logs stored per task (browsable like `session-replay.js`); preview renders produced files/static output.
  **Done when:** idea card → editable AI spec → sandboxed build → preview in dashboard; write-outside-sandbox attempt fails a test.

- [ ] **3.4 Image generation workflow** *(F1)*
  Files: new `skills/image-gen/`, new `server.py` media adapter (provider from settings, Gemini image first), artifacts page image preview
  **Done when:** prompt + style preset → image file in library; unconfigured provider shows graceful setup message.

- [ ] **3.5 Music & avatar video adapters** *(F2)*
  Files: same adapter interface as 3.4; providers configurable; audio/video previews in artifacts page
  **Done when:** with a configured provider, track/video lands in library; without, clean "not configured" state. (Defer to P2 if no provider access.)

- [ ] **3.6 Voice push-to-talk** *(G1)*
  Files: `dashboard/index.html` (mic button), new `dashboard/voice.js` (Web Speech API), `server.py` (route transcript via `/api/router/suggest` → skill + confirm)
  Confirmation chip before any run; unmatched commands ask, never guess. Update README to reflect real (not phantom) voice support.
  **Done when:** spoken "run the news oracle" in Chrome/Edge triggers the right skill after confirmation.

## Phase 4 — Sharing, Benchmarking, Polish (PRD Epic H + docs) `P1`

- [ ] **4.1 Save-file export/import** *(H1)*
  Files: `server.py` (new `/api/export`, `/api/import`), reuse tar logic from `/api/backup` (497–524), `dashboard/pages/backups.js` (export/import UI)
  Export excludes secrets/runtime/backups; import validates, reports missing deps (CLIs, keys, feeds) with instructions, never overwrites existing secrets.
  **Done when:** export→wipe-clone→import round-trip test passes with a dependency report.

- [ ] **4.2 Backend bench + leaderboard** *(H2)*
  Files: new `bench/tasks/*.json`, `server.py` (new `/api/bench/run`, `/api/bench/results`), new `dashboard/pages/bench.js` (extend `learning-analytics.js` chart patterns)
  Bench set runs across healthy agents; leaderboard: score/latency/cost; results exposed to router as `prefer: quality` ordering input (feeds 1.4).
  **Done when:** one command benches all healthy agents and the leaderboard renders; routing order observably reflects results.

- [ ] **4.3 README & claims audit** *(Goal 2, Metric)*
  Files: `README.md`, `AGENTS.md`, `docs/`
  Every feature claim verified against code; new features documented; comparison table updated; add PRD-V2/TASKS links.
  **Done when:** zero documented-but-unimplemented features remain.

---

## Dependency map

```
0.1 ─ 0.2 ─ 0.6 ──────────────► CI gate for everything after Phase 0
0.4 ─► 1.1 ─► 1.2 ─► 1.3 ─► 1.4
                        1.3 ─► 2.3 ─► 2.4 ◄─ 2.5
             2.1 ─► 2.2, 2.4, 3.4, 3.5
1.1 ─► 3.1 ─► 3.2        1.3 ─► 3.1
1.1 ─► 3.3               1.4 ─► 4.2
```

## Out of scope (per PRD-V2 non-goals — do not add "while we're at it")
Multi-tenant/auth · autonomous posting · frontend framework rewrite · removing free-tier agents · model training
