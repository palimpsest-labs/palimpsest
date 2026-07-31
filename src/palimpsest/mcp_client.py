"""MCP stdio client — thin wrapper around the standard `mcp` SDK.

Uses ``AsyncExitStack`` to manage transport + session lifecycles
without requiring an ``async with`` block (the web server reuses
Agent instances across ``run_turn`` calls).
"""

from __future__ import annotations

import os
import shutil
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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
        self._tools: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Launch the MCP server subprocess, initialise, and discover tools."""
        self._stack = AsyncExitStack()
        read_stream, write_stream = await self._stack.enter_async_context(
            stdio_client(self._params)
        )
        self._session = await self._stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()
        result = await self._session.list_tools()
        self._tools = [
            {"name": t.name, "description": t.description or "",
             "inputSchema": t.inputSchema}
            for t in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke a tool and return the joined text content."""
        if self._session is None:
            raise RuntimeError("MCP client not started — call start() first")
        result = await self._session.call_tool(name, arguments)
        texts = [c.text for c in result.content if c.type == "text"]
        return "\n".join(texts)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return tools discovered during initialisation."""
        return self._tools

    async def close(self) -> None:
        """Shut down the session and subprocess."""
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._session = None


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def get_memory_client(memory_path: str) -> MCPClient:
    """Create an MCP client connected to the memory-mcp knowledge-graph server."""
    node_bin = shutil.which("mcp-server-memory")
    if not node_bin:
        nvm_bin = os.path.expanduser(
            "~/.nvm/versions/node/v20.20.2/bin/mcp-server-memory"
        )
        if os.path.exists(nvm_bin):
            node_bin = nvm_bin
        else:
            raise FileNotFoundError(
                "mcp-server-memory not found. "
                "Install with: npm install -g @modelcontextprotocol/server-memory"
            )
    return MCPClient(
        StdioServerParameters(
            command=node_bin,
            args=[],
            env={"MEMORY_FILE_PATH": memory_path},
        ),
    )


def get_unified_history_client(config_path: str | None = None) -> MCPClient:
    """Create an MCP client connected to the unified-history-mcp server."""
    env = {}
    if config_path:
        env["UNIFIED_HISTORY_CONFIG"] = config_path
    return MCPClient(
        StdioServerParameters(
            command=sys.executable,
            args=["-m", "unified_history_mcp.server"],
            env=env if env else None,
        ),
    )
