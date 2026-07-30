# Palimpsest

**Open-source research engine for investigative journalists.**

Named for the medieval manuscript page scraped clean for reuse, where traces of the original text remain visible beneath the surface. Palimpsest uncovers what was written over.

## What it does

Journalists piece together stories from fragments — a GitHub profile here, a Companies House filing there, a Wayback Machine snapshot, a meeting transcript, a leaked chat log. Palimpsest connects these fragments into a structured investigation with source provenance, confidence ratings, and an immutable chain of custody.

A standalone agent that works with `ds4` (DwarfStar — [antirez/ds4](https://github.com/antirez/ds4)) for local LLM inference and [BigMoeOnEdge](https://github.com/Helldez/BigMoeOnEdge) as a phone companion for field work.

## Quick Start

```bash
# Install
pip install git+https://github.com/palimpsest-labs/palimpsest

# Create a case
palimpsest new my-investigation --title "My Investigation"

# Run the agent (requires ds4-server running on localhost:8000)
palimpsest agent my-investigation --message "Investigate..."
```

## The Toolkit

| Component | Role |
|---|---|
| `ds4` (DwarfStar) | Local LLM inference engine for DeepSeek V4 Flash on Apple Silicon |
| `BigMoeOnEdge` | Phone companion — runs MoE models on-device for field work |
| `mcp-server-memory` | Knowledge graph persistence (one per case) |
| `unified-history-mcp` | Full-text search across sessions, transcripts, notifications |
| `vibe-fst-indexer` | Blazing-fast FST search indexing (Rust) |
| `vibe-summarizer` | LLM-powered session and transcript condensation |
| `graph-gardener` | Knowledge graph maintenance — deduplication, enrichment, cleanup |

## Investigation Workflow

The methodology is code-enforced — phases can't be skipped, and dossier generation is gated on gap analysis plus confidence grading.

1. **Scope** — What's the question? Who's the subject?
2. **Map** — Build entity graph from what's known
3. **Enumerate** — Systematically check every platform for every entity
4. **Corroborate** — One source is a lead. Two is a finding. Three is confirmed.
5. **Synthesize** — Connect dots. Identify patterns. Flag contradictions.
6. **Gap analysis** — What's missing? What would confirm or refute?
7. **Report** — Generate dossier with confidence ratings and source index

### Phone Companion

Sync your case directory to your phone. Open `dossier.md` in any markdown reader (Obsidian, Markor). For on-device LLM queries, use [BigMoeOnEdge](https://github.com/Helldez/BigMoeOnEdge) — it runs 60GB MoE models on phones with 12GB RAM, CPU-only.

## Design Principles

- **Local-first** — sensitive investigations stay on your machine
- **Source provenance** — every finding traceable to origin
- **Confidence grading** — confirmed vs. circumstantial vs. speculative
- **Never delete** — append-only, immutable audit trail
- **Chain of custody** — legally defensible evidence capture
- **Offline-capable** — core functions work without internet

## License

MIT
