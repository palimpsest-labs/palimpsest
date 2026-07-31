"""Case directory management for palimpsest investigations.

Manages per-investigation case directories under ``~/.palimpsest/cases/<slug>/``.

Structure::

    ~/.palimpsest/cases/<slug>/
        memory.jsonl          # this case's knowledge graph
        captures/             # evidence snapshots
            manifest.jsonl    # hash-chained manifest
        state.json            # phase, open leads, hypothesis
        dossier.md            # generated output (created later)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_BASE = Path.home() / ".palimpsest" / "cases"

# Kebab-case: lowercase alphanumeric characters and hyphens, no leading/trailing
# hyphens, no consecutive hyphens, no spaces.
_VALID_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _default_base() -> Path:
    """Return the default base directory for cases, creating it if needed."""
    _DEFAULT_BASE.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_BASE


def _resolve_base(base_dir: str | None) -> Path:
    """Resolve the base directory from an optional string argument."""
    if base_dir is not None:
        return Path(base_dir)
    return _default_base()


def _initial_state(slug: str, title: str) -> dict[str, Any]:
    """Return the initial state dict for a new case."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "slug": slug,
        "title": title,
        "phase": "scope",
        "created": now,
        "updated": now,
        "open_leads": [],
        "working_hypothesis": None,
        "last_action": None,
        "next_action": None,
    }


def create_case(slug: str, title: str = "", base_dir: str | None = None) -> Path:
    """Create a full case directory structure under *base_dir*.

    The default base directory is ``~/.palimpsest/cases/``.

    Parameters
    ----------
    slug:
        Kebab-case identifier (lowercase alphanumeric characters separated by
        single hyphens).
    title:
        Human-readable case title (optional).
    base_dir:
        Override the default base directory.

    Returns
    -------
    Path to the created case directory.

    Raises
    ------
    ValueError
        If *slug* is not valid kebab-case, or if a case with this slug
        already exists.
    """
    if not _VALID_SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug {slug!r}: must be kebab-case "
            "(lowercase alphanumeric characters separated by single hyphens)"
        )

    base = _resolve_base(base_dir)
    case_dir = base / slug

    if case_dir.exists():
        raise ValueError(f"Case {slug!r} already exists at {case_dir}")

    # Create directory structure
    case_dir.mkdir(parents=True)
    (case_dir / "captures").mkdir()

    # Write initial state
    state = _initial_state(slug, title)
    (case_dir / "state.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Write empty manifest
    (case_dir / "captures" / "manifest.jsonl").write_text("", encoding="utf-8")

    return case_dir


def list_cases(base_dir: str | None = None) -> list[dict[str, Any]]:
    """List all case directories under *base_dir* with their metadata.

    Returns a list of dicts, each containing:
        slug, title, phase, created, updated, open_leads_count

    Directories that do not contain a valid ``state.json`` are skipped.
    """
    base = _resolve_base(base_dir)
    if not base.is_dir():
        return []

    results: list[dict[str, Any]] = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        state_path = entry / "state.json"
        if not state_path.is_file():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        results.append(
            {
                "slug": state.get("slug", entry.name),
                "title": state.get("title", ""),
                "phase": state.get("phase", "unknown"),
                "created": state.get("created"),
                "updated": state.get("updated"),
                "open_leads_count": len(state.get("open_leads", [])),
            }
        )

    return results


def get_case_dir(slug: str, base_dir: str | None = None) -> Path:
    """Return the case directory Path for *slug*.

    Raises FileNotFoundError if the directory does not exist.
    """
    if not _VALID_SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug {slug!r}: must be kebab-case "
            "(lowercase alphanumeric characters separated by single hyphens)"
        )
    base = _resolve_base(base_dir)
    case_dir = (base / slug).resolve()
    # Defence in depth: ensure the resolved path is inside the base
    resolved_base = base.resolve()
    if not str(case_dir).startswith(str(resolved_base) + os.sep) or case_dir == resolved_base:
        raise ValueError(f"Path traversal detected for slug {slug!r}")
    if not case_dir.is_dir():
        raise FileNotFoundError(f"Case {slug!r} not found at {case_dir}")
    return case_dir


def get_memory_path(slug: str, base_dir: str | None = None) -> Path:
    """Return the path to *memory.jsonl* for the given case.

    Creates the file (and the case directory, if it does not already exist)
    when missing.  Uses an atomic write to avoid TOCTOU races.
    """
    case_dir = get_case_dir(slug, base_dir)
    memory_path = case_dir / "memory.jsonl"
    if not memory_path.exists():
        # Atomic: write to temp file in same directory, then rename
        tmp_path = memory_path.with_suffix(".jsonl.tmp")
        tmp_path.write_text("", encoding="utf-8")
        os.replace(tmp_path, memory_path)
    return memory_path
