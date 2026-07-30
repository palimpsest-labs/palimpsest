# Palimpsest — Roadmap

## Vision

A local-first research engine for investigative journalists. Combines persistent memory, unified search across communication channels, platform APIs, web research, and LLM synthesis into a single tool that can build dossiers from fragments — and trace every finding back to its source.

The name: a **palimpsest** is a manuscript page from which text has been scraped or washed off so the page can be reused. Traces of the original remain visible beneath the surface. That's what this tool does.

## Phase 1 — Foundation

- [x] Repo scaffolding (pyproject.toml, LICENSE, .gitignore)
- [x] `research-tools.sh` — Wayback CDX, Companies House, WHOIS, RDAP
- [x] Evidence capture system — `capture.py` with SHA-256 + manifest.jsonl
- [x] Case directory system — `~/.palimpsest/cases/<slug>/` per-investigation isolation
- [x] State persistence — `state.json` (phase, leads, hypothesis, message history)
- [x] Methodology gates — phase state machine, dossier gating, system prompt generation
- [x] Agent loop — stdlib-only, OpenAI-compatible API (`/v1/chat/completions`)
- [x] Tool registry — 8 tools (memory×4 + research×4)
- [x] CLI — `palimpsest new|list|agent|dossier|wayback|company|whois|capture`
- [x] Documentation — README.md, CONTRIBUTING.md
- [x] Output templates — dossier.md, timeline.md, network-map.md
- [x] Vibe skill — SKILL.md (maintained as fallback for Vibe users)

## Phase 2 — Interface

The agent works. Now make it usable by actual journalists.

- [ ] **REPL** — readline conversation loop with the agent. State display (phase, open leads count). `/phase`, `/leads`, `/hypothesis`, `/save`, `/quit` commands. Session persistence across restarts.
- [ ] **Web interface** — `palimpsest serve` starts a local server, opens a browser tab. Single-page chat UI with:
  - [ ] Chat panel (SSE streaming, markdown rendering)
  - [ ] Phase indicator + progress bar
  - [ ] Evidence sidebar (captured sources with SHA-256 + wayback links)
  - [ ] Entity graph preview (Mermaid rendering)
  - [ ] Dossier preview panel
  - [ ] Zero build step — vanilla HTML/CSS/JS, served by the Python process
- [ ] **Mobile companion** — case directory sync (Syncthing/git) + BigMoeOnEdge integration guide + mobile-optimized dossier template

## Phase 3 — Integration

Wire up the backends properly.

- [ ] **ds4-server tested end-to-end** — full agent loop with DeepSeek V4 Flash on Apple Silicon
- [ ] **MCP memory integration** — agent reads/writes the knowledge graph via mcp-server-memory
- [ ] **MCP unified-history integration** — agent searches session history, transcripts, notifications
- [ ] **Hash-chained evidence manifest** — each manifest entry includes SHA-256 of previous entry for tamper detection
- [ ] **Graph-gardener integration** — periodic deduplication and cleanup of the investigation graph
- [ ] **Vibe-summarizer integration** — condense long tool results and conversation turns

## Phase 4 — Methodology Depth

The methodology is code-enforced. Now make it watertight.

- [ ] Legal jurisdiction awareness (UK: libel, GDPR, IPA considerations — configurable per jurisdiction)
- [ ] Adversarial threat model — encryption at rest (gocryptfs/age), source protection, export sanitization
- [ ] Temporal reasoning — date + precision + source for all events, timeline auto-generation
- [ ] Rate limiting and API etiquette — enforced in the tool layer, not just documented
- [ ] Deduplication — entity resolution in code (fuzzy name matching, merge prompts)
- [ ] Anti-bias protocol — deviation detection (did the agent search for disconfirming evidence?)
- [ ] **Golden-investigation eval** — synthetic case with planted contradiction + disconfirming trap, run on every model/backend change
- [ ] Synthetic demo dataset for onboarding and testing

## Phase 5 — Output

From raw investigation to polished product.

- [x] Dossier template — standardized markdown with players, timeline, evidence, verified vs. inferred
- [x] Timeline template — Mermaid gantt + markdown table
- [x] Network map template — Mermaid graph with legend
- [ ] **Automated dossier generation** — `palimpsest dossier <slug>` renders a complete dossier from the graph
- [ ] Gap analysis report — what's missing, what would confirm/refute, next leads
- [ ] PDF generation via pandoc (one-liner wrapper, not custom infrastructure)
- [ ] Source index with provenance URLs and access timestamps

## Phase 6 — Collaboration

Journalists work in teams. The tool should too.

- [ ] Git-based sharing — export entities to markdown, import from shared repo
- [ ] Entity conflict resolution strategy
- [ ] Export sanitization — strip confidential sources, internal notes, speculative findings
- [ ] Dossier packaging for external journalists — self-contained directory with all evidence
- [ ] Shared case directory over Syncthing or local network

## Phase 7 — Advanced

Scale, speed, and polish.

- [ ] SQLite-backed memory tier for large investigations (replaces JSONL at scale)
- [ ] Automatic Wayback cross-reference on every capture
- [ ] Confidence-weighted synthesis (Bayesian scoring for findings with mixed evidence)
- [ ] Multi-journalist real-time collaboration
- [ ] Managed hosting option for non-technical users
- [ ] Plugin system for additional platform APIs (OpenCorporates, certificate transparency, etc.)

## Design Principles (non-negotiable)

| Principle | What it means |
|---|---|
| **Local-first** | All data stored locally. Sensitive investigations shouldn't depend on cloud. |
| **Source provenance** | Every finding traceable to its origin — URL, timestamp, HTTP status, SHA-256. |
| **Confidence grading** | Confirmed / Circumstantial / Speculative. Assigned before synthesis, not after. |
| **Never delete** | Observations archived, not removed. Append-only audit trail. |
| **Offline-capable** | Core research functions work without internet. API calls are enrichment, not dependency. |
| **Chain of custody** | Immutable capture logs. Defensible in court. |
| **Zero build step** | The web interface is a single HTML file. No npm, no bundler, no framework. Open a browser tab. |
