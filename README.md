# Palimpsest

> *Ghost in the pages.*

**Open-source intelligence fusion tool for investigative journalists.**

Named for the medieval manuscript page scraped clean for reuse, where traces of the original text remain visible beneath the surface. Palimpsest uncovers what was written over.

## What it does

Journalists piece together stories from fragments — a GitHub profile here, a Companies House filing there, a Wayback Machine snapshot, a meeting transcript, a leaked chat log. Palimpsest connects these fragments into a structured investigation with source provenance, confidence ratings, and an immutable chain of custody.

A standalone agent that works with `ds4` (DwarfStar — [antirez/ds4](https://github.com/antirez/ds4)) for local LLM inference and [BigMoeOnEdge](https://github.com/Helldez/BigMoeOnEdge) as a phone companion for field work.

## The Toolkit

Twelve repos, one integrated pipeline:

| Repo | Role |
|---|---|
| **[palimpsest](https://github.com/palimpsest-labs/palimpsest)** | Research engine — local-first, source-tracked, methodology-enforced |
| **[unified-history-mcp](https://github.com/palimpsest-labs/unified-history-mcp)** | Cross-domain search across sessions, transcripts, notifications, and web archives |
| **[fst-indexer](https://github.com/palimpsest-labs/fst-indexer)** | Blazing-fast FST full-text search indexer (Rust) |
| **[memory-mcp](https://github.com/palimpsest-labs/memory-mcp)** | Persistent SQLite-backed knowledge graph |
| **[memory-stats-mcp](https://github.com/palimpsest-labs/memory-stats-mcp)** | Read-only graph stats and discovery |
| **[graph-gardener](https://github.com/palimpsest-labs/graph-gardener)** | LLM-powered knowledge graph maintenance |
| **[vibe-summarizer](https://github.com/palimpsest-labs/vibe-summarizer)** | LLM-powered session and transcript summarizer |
| **[web-archive-mcp](https://github.com/palimpsest-labs/web-archive-mcp)** | Persistent web fetch/search archiving — every result indexed forever |
| **[dns-whois-mcp](https://github.com/palimpsest-labs/dns-whois-mcp)** | DNS lookup and WHOIS registration research |
| **[image-analysis-mcp](https://github.com/palimpsest-labs/image-analysis-mcp)** | OCR, EXIF, and image metadata extraction |
| **[pdf-extract-mcp](https://github.com/palimpsest-labs/pdf-extract-mcp)** | PDF text and metadata extraction |
| **[shell-sandbox-mcp](https://github.com/palimpsest-labs/shell-sandbox-mcp)** | Safe shell commands via pledge()+unveil() with vendored busybox |

### How they connect

```
        capture / OSINT                     execution
 web-archive-mcp ──► JSONL archive          shell-sandbox-mcp
 dns-whois-mcp   ──► JSONL archive          pledge()+unveil()
 image-analysis  ──► OCR / EXIF             vendored busybox
 pdf-extract-mcp ──► extracted text
        │
        ▼
   fst-indexer ◄───────────────── unified-history-mcp
        │                             │
        ▼                             ▼
   memory-mcp ◄── graph-gardener  search across all
   memory-stats    (maintenance)  domains at once
   vibe-summarizer (summaries)
```

## Quick Start

```bash
# Install
pip install git+https://github.com/palimpsest-labs/palimpsest

# Create a case
palimpsest new my-investigation --title "My Investigation"

# Run the agent (requires ds4-server running on localhost:8000)
palimpsest agent my-investigation --message "Investigate..."
```

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
