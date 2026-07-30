"""Investigation state management — load/save state.json for a case."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STATE: dict[str, Any] = {
    "phase": "scope",
    "open_leads": [],
    "working_hypothesis": None,
    "last_action": None,
    "next_action": None,
    "agent_messages": [],  # serialised conversation for resume
}


def load_state(case_dir: Path) -> dict[str, Any]:
    """Load investigation state from state.json, merging with defaults."""
    state_file = case_dir / "state.json"
    if not state_file.exists():
        return dict(DEFAULT_STATE)
    with open(state_file) as f:
        saved = json.load(f)
    merged = dict(DEFAULT_STATE)
    merged.update(saved)
    return merged


def save_state(case_dir: Path, state: dict[str, Any]) -> None:
    """Save investigation state to state.json."""
    state["updated"] = datetime.now(timezone.utc).isoformat()
    state_file = case_dir / "state.json"
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2, default=str)


def update_state(case_dir: Path, **kwargs: Any) -> dict[str, Any]:
    """Load, update fields, and save state. Returns the new state."""
    state = load_state(case_dir)
    state.update(kwargs)
    state["updated"] = datetime.now(timezone.utc).isoformat()
    save_state(case_dir, state)
    return state
