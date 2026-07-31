"""Tool registry and execution layer for Palimpsest.

Wraps all available tools — memory graph, unified history, research utilities,
evidence capture, and web search — behind a uniform interface that the agent
loop can dispatch to.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .case import get_memory_path
from .capture import capture_url as do_capture

# Path to research-tools.sh, relative to this file
_TOOLS_SH = Path(__file__).resolve().parent.parent.parent / "research-tools.sh"


# ---------------------------------------------------------------------------
# Tool wrapper: each tool is a callable that returns a result string
# ---------------------------------------------------------------------------

class ToolResult:
    """Result of a tool execution, with structured content and metadata."""

    def __init__(self, content: str, is_error: bool = False, metadata: dict | None = None):
        self.content = content
        self.is_error = is_error
        self.metadata = metadata or {}


# ---------------------------------------------------------------------------
# Memory tools (synchronous wrappers around MCP — called via agent loop)
# ---------------------------------------------------------------------------

# These are defined as tool specs for the LLM, with execution handled
# by the agent loop calling the MCP client directly.
MEMORY_TOOLS = [
    {
        "name": "memory_search_nodes",
        "description": "Search for entities in the investigation knowledge graph by keyword.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query to match against entity names, types, and observations"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_create_entities",
        "description": "Create new entities in the investigation knowledge graph. Always search first to avoid duplicates.",
        "parameters": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "entityType": {"type": "string"},
                            "observations": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["name", "entityType", "observations"],
                    },
                },
            },
            "required": ["entities"],
        },
    },
    {
        "name": "memory_add_observations",
        "description": "Add observations to existing entities.",
        "parameters": {
            "type": "object",
            "properties": {
                "observations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entityName": {"type": "string"},
                            "contents": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["entityName", "contents"],
                    },
                },
            },
            "required": ["observations"],
        },
    },
    {
        "name": "memory_create_relations",
        "description": "Create relations between entities (works_at, follows, connected_to, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "relations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "relationType": {"type": "string"},
                        },
                        "required": ["from", "to", "relationType"],
                    },
                },
            },
            "required": ["relations"],
        },
    },
    {
        "name": "memory_delete_entities",
        "description": "Delete entities from the knowledge graph by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "entityNames": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names of entities to delete",
                },
            },
            "required": ["entityNames"],
        },
    },
    {
        "name": "memory_delete_observations",
        "description": "Delete specific observations from entities.",
        "parameters": {
            "type": "object",
            "properties": {
                "deletions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entityName": {"type": "string"},
                            "observations": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["entityName", "observations"],
                    },
                },
            },
            "required": ["deletions"],
        },
    },
    {
        "name": "memory_delete_relations",
        "description": "Delete relations between entities.",
        "parameters": {
            "type": "object",
            "properties": {
                "relations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "relationType": {"type": "string"},
                        },
                        "required": ["from", "to", "relationType"],
                    },
                },
            },
            "required": ["relations"],
        },
    },
    {
        "name": "memory_open_nodes",
        "description": "Open specific nodes in the knowledge graph by name. Returns full entity details including all observations and timestamps.",
        "parameters": {
            "type": "object",
            "properties": {
                "names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names of entities to open",
                },
            },
            "required": ["names"],
        },
    },
    {
        "name": "memory_read_graph",
        "description": "Read the entire knowledge graph. Returns all entities with observations and all relations.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "memory_traverse",
        "description": "Traverse the graph from a starting node, returning all entities within a given number of hops.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_node": {"type": "string", "description": "Entity name to start from"},
                "depth": {
                    "type": "integer",
                    "description": "Number of hops to traverse (default 1, max 3)",
                },
            },
            "required": ["start_node"],
        },
    },
    {
        "name": "memory_recent",
        "description": "Return entities and relations created or updated in the last N hours. Useful for seeing what changed recently.",
        "parameters": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Look-back window in hours (default 24, max 720)",
                },
            },
        },
    },
    {
        "name": "memory_search_similar",
        "description": "Fuzzy search for entity names using trigram similarity. Find entities with similar names even when you're unsure of the exact spelling.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to search for (fuzzy matched)"},
                "threshold": {
                    "type": "number",
                    "description": "Minimum similarity score 0.0–1.0 (default 0.3)",
                },
            },
            "required": ["name"],
        },
    },
]

# ---------------------------------------------------------------------------
# Research tools (subprocess wrappers)
# ---------------------------------------------------------------------------

RESEARCH_TOOLS = [
    {
        "name": "wayback_lookup",
        "description": "Fetch historical URL snapshots from the Wayback Machine. Returns a table of archived versions with timestamps and HTTP status codes.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to look up in the Wayback Machine"},
                "from_year": {"type": "integer", "description": "Optional: earliest year to include"},
                "to_year": {"type": "integer", "description": "Optional: latest year to include"},
                "limit": {"type": "integer", "description": "Optional: max results (default 100)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "companies_house_lookup",
        "description": "Look up a UK company on Companies House. Returns company profile and officer list. Requires COMPANIES_HOUSE_API_KEY environment variable.",
        "parameters": {
            "type": "object",
            "properties": {
                "company_number": {"type": "string", "description": "UK company registration number (e.g. 11311496)"},
            },
            "required": ["company_number"],
        },
    },
    {
        "name": "whois_lookup",
        "description": "Look up domain WHOIS information. Returns registrar, creation date, expiry date, and nameservers.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain name to look up (e.g. example.com)"},
            },
            "required": ["domain"],
        },
    },
    {
        "name": "evidence_capture",
        "description": "Capture a web page as evidence. Saves HTML snapshot with SHA-256 hash and adds an entry to the chain-of-custody manifest. Always use this before citing a URL as a source.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to capture as evidence"},
            },
            "required": ["url"],
        },
    },
]


def run_research_tool(name: str, args: dict[str, Any], case_dir: Path) -> ToolResult:
    """Execute a research tool via research-tools.sh or capture.py."""
    try:
        if name == "wayback_lookup":
            cmd = [str(_TOOLS_SH), "wayback", args["url"], "--json"]
            if args.get("from_year"):
                cmd += ["--from", str(args["from_year"])]
            if args.get("to_year"):
                cmd += ["--to", str(args["to_year"])]
            if args.get("limit"):
                cmd += ["--limit", str(args["limit"])]

        elif name == "companies_house_lookup":
            cmd = [str(_TOOLS_SH), "companies-house", args["company_number"], "--json"]

        elif name == "whois_lookup":
            cmd = [str(_TOOLS_SH), "whois", args["domain"], "--json"]

        elif name == "evidence_capture":
            captures_dir = str(case_dir / "captures")
            return _run_capture(args["url"], captures_dir)

        else:
            return ToolResult(f"Unknown tool: {name}", is_error=True)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        if result.returncode != 0:
            return ToolResult(
                f"Tool '{name}' failed (exit {result.returncode}):\n{result.stderr}",
                is_error=True,
            )
        return ToolResult(result.stdout.strip() or "(empty result)")

    except subprocess.TimeoutExpired:
        return ToolResult(f"Tool '{name}' timed out after 35 seconds.", is_error=True)
    except Exception as e:
        return ToolResult(f"Tool '{name}' error: {e}", is_error=True)


def _run_capture(url: str, captures_dir: str) -> ToolResult:
    """Run capture.py for evidence capture."""
    try:
        from .capture import capture_url
        entry = capture_url(url, captures_dir)
        return ToolResult(
            f"Evidence captured.\n"
            f"URL: {entry['url']}\n"
            f"Status: {entry['status_code']}\n"
            f"SHA-256: {entry['sha256']}\n"
            f"Wayback: {entry.get('wayback_url') or 'none'}\n"
            f"Content-Type: {entry.get('content_type', 'unknown')}\n"
            f"Manifest: {captures_dir}/manifest.jsonl",
            metadata={"entry": entry},
        )
    except Exception as e:
        return ToolResult(f"Capture failed: {e}", is_error=True)


# ---------------------------------------------------------------------------
# All available tools (combined for the LLM)
# ---------------------------------------------------------------------------

def get_all_tool_definitions() -> list[dict]:
    """Return all tool definitions for the LLM."""
    tools = []
    tools.extend(MEMORY_TOOLS)
    tools.extend(RESEARCH_TOOLS)
    return tools
