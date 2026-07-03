# PRD: Agentic OS — Personal AI Mission Control

| | |
|---|---|
| **Status** | Draft v1.0 |
| **Author** | James Glen (with Claude Code) |
| **Date** | 2026-07-03 |
| **Source** | Capability analysis of "NEW Claude Agentic OS is INSANE!" (Julian Goldie Podcast, [youtube.com/watch?v=1EloYKa_VTc](https://www.youtube.com/watch?v=1EloYKa_VTc)) — full transcript reviewed; see Appendix A for capability-to-requirement traceability |

---

## 1. Problem Statement

People who work with AI daily spread their work across chat apps, terminals, CLIs, and a dozen browser tabs. Workflows they've already figured out (news research → SEO article, thumbnail generation, avatar videos, social drafts) get re-prompted from scratch each time, past conversations are unfindable ("where was that thread about open SEO last week?"), and context/memory is trapped inside each vendor's product. The result is repeated effort, lost context, vendor lock-in (one provider outage takes down everything), and a constant feeling of falling behind each new model release.

**Agentic OS** is a self-hosted, fully customizable mission-control dashboard that puts every agent, CLI, and custom workflow one click away — with a shared persistent memory that makes every workflow smarter over time, and a provider-agnostic model layer so the system survives any single vendor going down.

## 2. Goals

1. **One-click execution** — every recurring AI workflow (SEO, social drafts, images, avatar video, music, news digest) runs from a single click or voice command; no re-prompting, no tab-hunting. *Target: median clicks from dashboard to workflow output ≤ 2.*
2. **Radical time reduction** — a full trending-news → SEO article → social drafts cycle completes in under 5 minutes of human attention (vs. ~1–2 hours manual).
3. **Provider independence** — the OS keeps functioning when any single model provider is down; every workflow can run on at least two backends (cloud API, CLI, or local model). *Target: 100% of P0 workflows have a configured fallback.*
4. **Compounding memory** — every workflow run automatically writes to and reads from a shared memory store, so output quality/personalization improves with use. *Target: 100% of workflow runs recorded; memory retrieval used in 100% of generation workflows.*
5. **Same-day extensibility** — a new model, CLI, or workflow can be integrated and live on the dashboard within one working day, by editing config/plugin files only (no core code changes).
6. **Near-zero marginal cost option** — every P0 workflow can run in a "free/local" mode (local models, free-tier APIs, already-owned CLI subscriptions) with per-run cost visible.

## 3. Non-Goals

1. **Not a SaaS / multi-tenant product (v1).** Single-user, self-hosted, local-first. Multi-user auth, billing, and hosting are a separate future initiative.
2. **Not a general chat client.** The unit of work is a *workflow tile*, not an open-ended chat thread. Ad-hoc chat exists only as a utility panel; we are not competing with Claude.ai/ChatGPT on chat UX.
3. **Not building our own models or fine-tuning.** We orchestrate existing APIs, CLIs, and local runtimes (Ollama etc.); training infrastructure is out of scope.
4. **No autonomous external publishing in v1.** Workflows produce *drafts* (SEO articles, social posts, videos); a human approves before anything is posted to an external platform. Fully autonomous posting is P2 — the blast radius of a bad auto-post outweighs the click it saves.
5. **Not a mobile app.** Responsive desktop web only; mobile-native is premature until desktop usage patterns are established.

## 4. Users & Personas

- **The Operator (primary)** — solo AI-native builder/marketer/agency owner. Runs content and client workflows daily, comfortable with terminals and API keys, wants everything automated and personalized. Spends hours/day inside the system and iterates on it constantly.
- **The Tinkerer (secondary)** — community member who installs the Operator's system, then customizes tiles, themes, and workflows for their own niche. Needs import/export and safe customization, not deep code skills.
- **The Client-Server (tertiary, P2)** — the Operator's client who receives generated artifacts and auto-generated documentation sites, but never touches the dashboard.

## 5. User Stories

**Dashboard & orchestration**
- As an operator, I want all my agents, CLIs, and workflows on one dashboard so that I never hunt through apps or old conversations to find a capability. (P0)
- As an operator, I want to run any workflow with one click (with sensible saved defaults) so that recurring work costs me seconds, not sessions. (P0)
- As an operator, I want to hide, remove, reorder, and re-theme any tile or section so that the OS looks and feels exactly how I designed it. (P0)
- As an operator, I want to trigger workflows by voice so that I can operate the system hands-free. (P1)

**Content engine**
- As an operator, I want a news oracle that pulls the latest news every 24 hours and auto-categorizes it by trending topic so that I never have to search Twitter/news manually. (P0)
- As an operator, I want to generate an SEO article from any trending topic in one click so that content production is tied directly to what's trending. (P0)
- As an operator, I want one-click social media drafts linked to a trending topic so that distribution content is ready the moment the news lands. (P0)
- As an operator, I want one-click image/thumbnail generation, AI avatar video generation, and music generation so that all media production lives in the same system. (P0 image, P1 video/music)
- As an operator, I want to bookmark/save any generated artifact so that I can find and reuse it later. (P0)

**Model layer**
- As an operator, I want each workflow routable to a cloud API, an installed CLI, or a local model so that I control cost and I'm never blocked by one provider's outage. (P0)
- As an operator, I want a benchmark/leaderboard view comparing models I've tested so that routing decisions are based on my own results, not hype. (P1)

**Memory**
- As an operator, I want every workflow run to automatically update a shared memory store so that the system gets more personalized every time I use it. (P0)
- As an operator, I want to browse and search all memories (including a visual "galaxy" view) so that past context is always findable. (P0 search/browse, P1 galaxy visualization)

**Multi-agent orchestration**
- As an operator, I want to define an org chart of role-based agents (e.g., CEO, CTO, sales) that can delegate a goal into subtasks so that multi-step projects run like a zero-human company. (P1)
- As an operator, I want an ideas-to-implementation pipeline (idea → spec → build → preview) so that a new feature idea becomes a working, previewable artifact without leaving the OS. (P1)

**Self-documentation & sharing**
- As an operator, I want everything I build and test to be automatically documented into a browsable site so that I (and clients) can see what was built, why, and how models compare. (P1)
- As a tinkerer, I want to export/import the entire OS configuration as a "save file" so that I can install someone's system and make it mine. (P1)

**Edge cases**
- As an operator, when a provider call fails, I want automatic fallback to the next configured backend and a visible notice so that a workflow never silently dies. (P0)
- As an operator, when a scheduled job fails overnight, I want it retried and surfaced on the dashboard so that stale data is never mistaken for fresh. (P0)
- As a tinkerer, when I import a save file, I want secrets excluded and missing dependencies (CLIs, local models, API keys) listed so that setup failures are diagnosable. (P1)

## 6. Requirements

### P0 — Must-Have (v1 cannot ship without these)

**R1. Mission Control Dashboard**
Single-page web app (self-hosted, localhost-first) presenting all capabilities as tiles organized into user-defined sections.
- [ ] Tiles render for every registered workflow, agent, and CLI; clicking a tile runs it or opens its panel
- [ ] Drag-to-reorder tiles and sections; hide/show and delete from a settings side panel
- [ ] Theming: at minimum accent color, background, section names; layout persists across restarts
- [ ] Global search over tiles, workflows, past runs, and memories
- [ ] Live status per tile: idle / running / failed / last-run timestamp

**R2. Workflow Engine ("one click")**
Declarative workflow definitions (YAML/JSON + optional script step) chaining steps: prompt → model call → tool/CLI call → output.
- [ ] Workflows are files in a `workflows/` directory; hot-reloaded onto the dashboard without core code changes
- [ ] Each workflow declares inputs (with saved defaults so one click = run), model routing preference, and output type (markdown, image, audio, video, file)
- [ ] Given a workflow with saved defaults, when the tile is clicked, then it runs end-to-end with no further input
- [ ] Run history persisted per workflow: inputs, outputs, model used, tokens, cost, duration
- [ ] Failed step ⇒ retry once, then fall back to next configured model backend, then surface error state on the tile — never a silent failure

**R3. Provider-Agnostic Model Layer**
One internal interface with adapters for: cloud APIs (Anthropic first, then OpenAI-compatible endpoints), installed CLIs (Claude Code headless mode as the primary agent engine), and local models (Ollama / OpenAI-compatible local server).
- [ ] Per-workflow routing config: ordered backend list (e.g., `claude-fable-5 → claude-code-cli → ollama:qwen`)
- [ ] Global "free/local mode" toggle forces all routing to local/free backends
- [ ] Per-run token and cost tracking rolled up on a dashboard cost widget
- [ ] Given the primary provider is unreachable, when a workflow runs, then it completes on a fallback backend and the run record notes the substitution

**R4. Scheduler**
Cron-style scheduling of any workflow.
- [ ] Schedules defined in workflow config (e.g., news refresh every 24h)
- [ ] Missed/failed scheduled runs are retried (bounded) and flagged on the dashboard with the data's actual age
- [ ] Manual "run now" always available

**R5. News Oracle**
Scheduled workflow pulling latest news for configured topics (RSS/APIs/search), then LLM-clustering into trending topics.
- [ ] Refreshes automatically every 24h (configurable); dashboard panel shows topics ranked by trend strength with source links
- [ ] Each topic card exposes one-click actions: *SEO article*, *social drafts* (context of the topic is passed automatically)
- [ ] Topic history retained so past days remain browsable

**R6. Content Workflows (shipped as built-in examples of R2)**
- [ ] **SEO article**: topic (or trending-topic card) → outlined, keyword-aware long-form draft in markdown, saved to library
- [ ] **Social drafts**: topic → platform-tailored post set (X, LinkedIn minimum) linked back to the source topic
- [ ] **Image/thumbnail**: prompt + saved style presets → image via configured backend, saved to library
- [ ] All outputs are drafts in the library — nothing auto-publishes externally (see Non-Goal 4)

**R7. Shared Memory Store**
Persistent memory (structured files + embeddings index) automatically read and written by all workflows.
- [ ] Every workflow run appends memory entries (what ran, key facts/preferences extracted)
- [ ] Generation workflows retrieve relevant memories and inject them into context (personalization)
- [ ] Memory browser UI: list, full-text/semantic search, view, edit, delete any memory
- [ ] Memories are plain files on disk — user-ownable, portable, no vendor lock-in

**R8. Artifact Library**
Central store for all generated outputs (articles, images, audio, video, docs).
- [ ] Every workflow output lands in the library with metadata (workflow, date, model, source topic)
- [ ] Bookmark/favorite, tag, search, preview inline, open file location
- [ ] Nothing generated is ever lost — library is append-only unless the user deletes

### P1 — Nice-to-Have (fast follows)

**R9. Voice Agent** — push-to-talk (and wake word if feasible) mapped to workflow triggers; local STT (e.g., Whisper) preferred. Acceptance: "run the news refresh" spoken ⇒ correct workflow runs; unmatched commands ask for confirmation rather than guessing.

**R10. Agent Orchestration ("zero-human company")** — define role agents (CEO/CTO/Sales/etc.) in config with persona, tools, and model; submit a goal, orchestrator decomposes to roles, runs subtasks (parallel where independent), aggregates results; live org-chart view of task flow. Human approval gate before any external side effect.

**R11. Ideas-to-Implementation Pipeline** — kanban: Idea → Spec → Build → Preview. "Build" hands the spec to the agent engine (Claude Code headless) in a sandboxed project directory; "Preview" serves the result in an embedded pane. All builds sandboxed to their own directory.

**R12. Auto-Documentation Site** — every completed build/test generates or updates a static docs site (what was built, why, how it works, model comparison pages). Regenerated on change; served locally; exportable for sharing with clients.

**R13. Benchmark / Leaderboard ("Bench")** — define eval tasks; run them across configured backends; leaderboard view with scores, latency, and cost; results feed routing recommendations.

**R14. AI Avatar Video + Music Generation workflows** — one-click tiles wrapping configured providers (e.g., HeyGen-class avatar API; Suno-class or local music model). Genre/style presets; outputs land in the library with bookmark support (music: prompt → playable track in ≤ ~3 min).

**R15. Save File (export/import)** — export entire OS config (layout, themes, workflows, agent definitions, schedules — *excluding secrets*) as a single archive; import validates and lists missing dependencies (API keys, CLIs, local models) with setup instructions.

### P2 — Future Considerations (design for, don't build)

- **Approved auto-publishing**: per-workflow "auto-post" with allowlisted destinations, once draft-quality trust is established.
- **Multi-user / team mode**: auth, roles, shared memory namespaces.
- **Plugin marketplace / community workflow sharing** beyond manual save-file exchange.
- **Mobile companion** (trigger + notifications only).
- **Architectural insurance now**: keep all state in plain files under one root dir (enables sync/multi-user later); keep workflow schema versioned (enables marketplace); keep publishing behind a single gateway module (enables auto-post allowlists).

## 7. System Architecture (informative)

```
┌─────────────────────────── Dashboard (web UI, localhost) ───────────────────────────┐
│  Tiles/sections • settings & theming • memory galaxy • library • org chart • bench  │
└──────────────────────────────────────┬───────────────────────────────────────────────┘
                                       │ HTTP/WebSocket
┌──────────────────────────────────────┴───────────────────────────────────────────────┐
│                         Core service (single local process)                          │
│  Workflow engine ── Scheduler ── Orchestrator ── Memory store ── Artifact library     │
│                                       │                                               │
│                          Model routing layer (fallback chains, cost meter)            │
└───────┬───────────────────┬───────────────────────┬──────────────────────┬───────────┘
   Cloud APIs        Claude Code CLI          Local models            Media/tool APIs
 (Anthropic, etc.)   (headless agent engine)  (Ollama, etc.)     (image, avatar, music,
                                                                  news/RSS, search)
```

- **Stack suggestion**: TypeScript/Node core + React dashboard (or Python/FastAPI + React); SQLite for run history; files + a local embeddings index for memory; everything under one user-owned root directory.
- **Claude Code as agent engine**: build/test/orchestration tasks shell out to `claude` in headless mode with skills, matching the source system's approach.
- **Security**: secrets in a local `.env`/OS keychain, never in save files; the dashboard binds to localhost by default; every workflow with external side effects passes through one publishing gateway module (P2 gate).

## 8. Success Metrics

**Leading (evaluate 2 weeks post-v1)**
- Median clicks from dashboard open → workflow output: **≤ 2** (measure via UI telemetry, local only)
- News → SEO article → social drafts cycle: **≤ 5 min** human attention (timed runs)
- Workflow run success rate (incl. fallback saves): **≥ 95%**; silent failures: **0**
- Workflows with a working fallback backend: **100% of P0 set**

**Lagging (evaluate 1–3 months)**
- Daily active use of the dashboard (self-measured streak): **≥ 5 days/week**
- Share of content output produced through the OS vs. ad-hoc chat tools: **≥ 80%**
- New capability integration time (new model/CLI/workflow to live tile): **≤ 1 day**, config-only
- Marginal cost per SEO article in free/local mode: **≈ $0** (cost meter)

## 9. Open Questions

| # | Question | Owner | Blocking? |
|---|----------|-------|-----------|
| 1 | Core stack: TypeScript/Node vs. Python for the core service? (Dashboard is React either way) | Engineering | Yes — decide before build |
| 2 | News sources for the Oracle: RSS-only (free, reliable) vs. adding a paid news/search API for trend strength? | Product | No — start RSS, extend |
| 3 | Which avatar-video and music providers, given cost and ToS on generated content? | Product/Legal | No — P1 |
| 4 | Local STT (Whisper) footprint acceptable on target machine, or cloud STT fallback? | Engineering | No — P1 |
| 5 | Memory extraction policy: what gets auto-remembered from runs, and what requires explicit "remember this"? (privacy + noise tradeoff) | Product | Yes for R7 design |
| 6 | Multi-agent runaway protection: max depth/spend per orchestration run? | Engineering | Yes for R10 |

## 10. Timeline & Phasing

No hard external deadline; phases sized for a solo builder using Claude Code, biased toward a usable dashboard early (the source system was built by daily 3–4h iteration — this plan assumes the same cadence).

- **Phase 1 — Skeleton (Week 1–2):** Core service + dashboard shell, workflow engine (R2), model routing layer (R3), one end-to-end workflow (SEO article) with fallback. *Exit: one tile, one click, one article, provider outage survivable.*
- **Phase 2 — Daily driver (Week 3–4):** Scheduler (R4), News Oracle (R5), remaining content workflows (R6), artifact library (R8), dashboard customization (R1 complete). *Exit: the OS replaces manual news+content routine.*
- **Phase 3 — Compounding (Week 5–6):** Shared memory store + browser (R7), cost meter polish, save-file export/import (R15). *Exit: system gets smarter with use and is shareable.*
- **Phase 4 — Force multipliers (Week 7–10):** Voice agent (R9), agent orchestration (R10), ideas-to-implementation pipeline (R11), auto-docs (R12), bench/leaderboard (R13), avatar video + music (R14).

Dependencies: R5/R6 depend on R2+R3; R10/R11 depend on Claude Code headless integration (part of R3); R12 depends on R11 artifacts existing; R13 depends on R3's adapter interface.

---

## Appendix A — Video Capability → Requirement Traceability

| Video (timestamp) | Capability shown | Requirement |
|---|---|---|
| 00:00–00:15 | Mission control dashboard, all agents/workflows in one system | R1 |
| 00:15–00:17 | Create and preview anything built (mixture of agents) | R11 |
| 00:19–00:36 | "Hermes Oracle" news pull, SEO content, one-click social drafts, 24h trending categorization | R5, R6 |
| 00:37 | Voice-activated agent | R9 |
| 00:39–00:41 | Ideas-to-implementation pipeline | R11 |
| 01:12–01:23 | One-click images/thumbnails, AI avatar videos, SEO automation | R6, R14 |
| 01:52–02:09 | Free APIs, cheap APIs, existing CLIs, local models — minimal token cost | R3 |
| 02:24–02:47 | Fully custom look/feel; hide/delete anything in settings | R1 |
| 02:52–02:57 | Survives a model provider going down | R3 (fallback chains) |
| 03:12–03:23 | New model integrated within 48h of release | Goal 5, R2 hot-reload |
| 03:27–03:53 | Auto-documented into a website; model comparison pages | R12 |
| 04:17–04:57 | Multi-agent org: CEO/CTO agents, "zero-human company", sales sections | R10 |
| 05:04–05:22 | On-the-spot music generation (~2 min), bookmark/save | R14, R8 |
| 06:05–06:36 | "Memory galaxy": auto-updated, browsable, searchable memories feeding every workflow/agent/CLI | R7 |
| 07:13–07:21 | Built on Claude Code + skills ("superpowers") | Architecture §7 |
| 09:16–09:26 | Auto-refreshing news dashboard (never search Twitter again) | R4, R5 |
| 10:52 | Distributable "save file" installed by community members | R15 |
| 11:00–11:16 | Local AI testing leaderboards ("Goldy Bench") | R13 |

*Note: the video markets a paid community product and does not show implementation internals; this PRD specifies equivalent capabilities from the demonstrated behavior. Product names in the transcript (e.g., "Hermes Oracle", "Paperclip") are auto-captioned and may be inexact.*
