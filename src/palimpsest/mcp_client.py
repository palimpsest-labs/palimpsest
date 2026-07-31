"""MCP stdio client — thin wrapper around the standard `mcp` SDK.

Uses ``AsyncExitStack`` to manage transport + session lifecycles
without requiring an ``async with`` block (the web server reuses
Agent instances across ``run_turn`` calls).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import traceback
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Default timeout for MCP tool calls (seconds)
DEFAULT_TOOL_TIMEOUT = 30


class MCPClient:
    """MCP stdio client backed by the standard `mcp` SDK.

    Starts a child process, negotiates the MCP handshake, and exposes
    ``call_tool``.  Call ``start()`` before use and ``close()`` when
    done — both are driven by `AsyncExitStack`.
    """

    def __init__(self, params: StdioServerParameters):
        self._params = params
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._tool_names: frozenset[str] = frozenset()

    async def start(self) -> None:
        """Launch the MCP server subprocess, initialise, and discover tools."""
        self._stack = AsyncExitStack()
        try:
            read_stream, write_stream = await self._stack.enter_async_context(
                stdio_client(self._params)
            )
            self._session = await self._stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._session.initialize()
            result = await self._session.list_tools()
            self._tool_names = frozenset(t.name for t in result.tools)
        except Exception:
            await self._stack.aclose()
            self._stack = None
            self._session = None
            self._tool_names = frozenset()
            raise

    async def call_tool(self, name: str, arguments: dict[str, Any],
                        timeout: float = DEFAULT_TOOL_TIMEOUT) -> tuple[str, bool]:
        """Invoke a tool and return ``(text, is_error)``.

        *is_error* is True when the MCP server reports the tool errored
        (``result.isError``) or when no text content was produced.
        """
        if self._session is None:
            raise RuntimeError("MCP client not started — call start() first")
        result = await asyncio.wait_for(
            self._session.call_tool(name, arguments),
            timeout=timeout,
        )
        texts = [c.text for c in result.content if c.type == "text"]

        if not texts:
            # No text content; provide a diagnostic
            type_summary = ", ".join(
                f"{getattr(c, 'type', '?')}" for c in result.content
            ) if result.content else "empty"
            if result.isError:
                return f"(server error — no text content; content types: {type_summary})", True
            return f"(no text content returned; content types: {type_summary})", False

        return "\n".join(texts), result.isError

    def knows(self, name: str) -> bool:
        """Return True if *name* is among the tools exposed by the server."""
        return name in self._tool_names

    async def close(self) -> None:
        """Shut down the session and subprocess."""
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except Exception:
                traceback.print_exc(file=sys.stderr)
            self._stack = None
            self._session = None
            self._tool_names = frozenset()


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

# Resolution order for the memory knowledge-graph server:
#  1. `memory-mcp`     — our SQLite fork (canonical)
#  2. `memory-mcp` via nvm path
#  3. `mcp-server-memory` — upstream JSONL fallback
def _resolve_memory_bin() -> str:
    """Find the memory knowledge-graph server binary."""
    candidates = [
        shutil.which("memory-mcp"),
        os.path.expanduser("~/.nvm/versions/node/v20.20.2/bin/memory-mcp"),
        shutil.which("mcp-server-memory"),
        os.path.expanduser(
            "~/.nvm/versions/node/v20.20.2/bin/mcp-server-memory"
        ),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError(
        "memory-mcp not found. Is memory-mcp installed and on PATH? "
        "Install memory-mcp from the palimpsest-labs toolkit."
    )


def get_memory_client(memory_path: str) -> MCPClient:
    """Create an MCP client connected to the memory-mcp knowledge-graph server."""
    return MCPClient(
        StdioServerParameters(
            command=_resolve_memory_bin(),
            args=[],
            env={"MEMORY_FILE_PATH": memory_path},
        ),
    )


def get_unified_history_client(config_path: str | None = None) -> MCPClient:
    """Create an MCP client connected to the unified-history-mcp server."""
    env: dict[str, str] = {}
    if config_path:
        env["UNIFIED_HISTORY_CONFIG"] = config_path
    return MCPClient(
        StdioServerParameters(
            command=sys.executable,
            args=["-m", "unified_history_mcp.server"],
            env=env if env else None,
        ),
    )
