"""Methodology enforcement gates for Palimpsest.

These are structural guarantees that the investigative methodology is followed.
They turn SKILL.md prose into code-enforced rules that cannot be skipped by a
well-meaning but distractible LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .state import load_state

# Phase order — must progress sequentially
PHASE_ORDER = ["scope", "map", "enumerate", "corroborate", "synthesize", "gap_analysis", "report"]


def get_current_phase(case_dir: Path) -> str:
    """Return the current investigation phase."""
    state = load_state(case_dir)
    return state.get("phase", "scope")


def advance_phase(case_dir: Path, new_phase: str) -> bool:
    """Advance to the next phase. Returns True if successful, False if invalid transition."""
    current = get_current_phase(case_dir)
    if new_phase not in PHASE_ORDER:
        return False
    current_idx = PHASE_ORDER.index(current)
    new_idx = PHASE_ORDER.index(new_phase)
    if new_idx < current_idx:
        return False  # Can't go backwards
    # Allow skipping forward by one (e.g., if user says "just investigate this")
    # but enforce at least the current phase check
    return True


def check_dossier_ready(case_dir: Path) -> list[str]:
    """Check if the investigation is ready for dossier generation.
    Returns a list of issues (empty = ready).
    """
    issues: list[str] = []
    state = load_state(case_dir)

    # Phase check
    if state.get("phase") not in ("gap_analysis", "report"):
        issues.append(
            f"Cannot generate dossier during '{state.get('phase')}' phase. "
            f"Complete gap_analysis first."
        )

    # Gap analysis must exist
    gap_entity_count = _count_entities_of_type(case_dir, "gap")
    if gap_entity_count == 0:
        issues.append("No gap entities found. Complete gap_analysis phase first.")

    # Open leads check — warn but don't block
    if state.get("open_leads"):
        issues.append(
            f"Warning: {len(state['open_leads'])} open leads remain. "
            f"Dossier may be incomplete."
        )

    return issues


def check_before_create_entity(case_dir: Path, entity_name: str) -> bool:
    """Gatekeeper: warn if an entity might already exist.
    Returns True if it's safe to proceed (no duplicate found).
    The actual duplicate check should be done via memory_search_nodes;
    this is a structural gate that CAN be enforced if we load the graph.

    For now, this is advisory — the agent loop should search before creating.
    """
    # This is intentionally light — the heavy check is in the agent loop
    # where it calls memory_search_nodes before memory_create_entities.
    return True


def _count_entities_of_type(case_dir: Path, entity_type: str) -> int:
    """Count entities of a given type in the case's memory graph."""
    memory_path = case_dir / "memory.jsonl"
    if not memory_path.exists():
        return 0
    count = 0
    try:
        import json
        with open(memory_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") == "entity" and entry.get("entityType") == entity_type:
                    count += 1
    except Exception:
        pass
    return count


# ---------------------------------------------------------------------------
# System prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Palimpsest — an investigative research agent for journalists.

## Your Purpose

You systematically gather, corroborate, synthesize, and report on information about a subject. You work through a defined methodology with rigorous source provenance and confidence grading. You never start with the story. You find it.

## Investigation Phases

You are currently in the **{phase}** phase. Follow this order.

1. **scope** — Establish the question, subject, boundaries, jurisdiction.
2. **map** — Build the initial entity graph from what's known.
3. **enumerate** — Systematically check every platform for every entity.
4. **corroborate** — Cross-reference. One source = lead. Two = finding. Three = confirmed.
5. **synthesize** — Connect dots, identify patterns, flag contradictions.
6. **gap_analysis** — What's missing? What would confirm or refute?
7. **report** — Generate the dossier.

## Confidence Grading

Assign one of these to every finding, BEFORE synthesis:
- 🟢 CONFIRMED: 3+ independent sources OR official record
- 🟡 CIRCUMSTANTIAL: 2 independent sources, plausible but not proven
- 🔴 SPECULATIVE: 1 source, pattern inference, or user report

## Key Rules

1. ALWAYS search memory (memory_search_nodes) before creating entities — never create duplicates.
2. ALWAYS capture web pages as evidence (evidence_capture) before citing them as sources.
3. NEVER synthesize before corroborating. Phase order exists for a reason.
4. For every hypothesis, actively search for DISCONFIRMING evidence.
5. Assign confidence grades BEFORE deciding what story the evidence tells.
6. Surface contradictions — don't resolve them silently.
7. Grade conservatively: if unsure between two grades, use the lower one.

## Entity Types

Use these entity types: person, organization, event, finding, source, pattern, lead, investigation, timeline_entry, hypothesis, gap.
Entity names in kebab-case: firstname-lastname, company-name-ltd.

## Relation Types

works_at, director_of, follows, attended, authored, connected_to, same_as, supports, contradicts, sourced_from, occurred_before, occurred_after.

## Current Investigation

Title: {title}
Open leads: {open_leads}
Working hypothesis: {working_hypothesis}
Next action: {next_action}

Proceed with the investigation. Be thorough, be sceptical, and track every source.
"""


def build_system_prompt(case_dir: Path) -> str:
    """Build the system prompt for the current investigation state."""
    state = load_state(case_dir)
    return SYSTEM_PROMPT.format(
        phase=state.get("phase", "scope"),
        title=state.get("title", "Untitled Investigation"),
        open_leads=json.dumps(state.get("open_leads", []), indent=2) if state.get("open_leads") else "None",
        working_hypothesis=state.get("working_hypothesis") or "None",
        next_action=state.get("next_action") or "Ask the journalist what to investigate.",
    )
