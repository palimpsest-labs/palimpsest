"""MCP stdio client for memory and unified-history servers."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class MCPClient:
    """Minimal MCP stdio client. Talks JSON-RPC over stdin/stdout to a child process."""

    def __init__(self, command: list[str], env: dict[str, str] | None = None):
        self.command = command
        self.env = env
        self.process: subprocess.Popen | None = None
        self._request_id = 0
        self._tools: list[dict] = []

    async def start(self) -> None:
        merged_env = os.environ.copy()
        if self.env:
            merged_env.update(self.env)
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            env=merged_env,
            text=True,
        )
        # Initialise
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "palimpsest", "version": "0.1.0"},
        })
        # Discover tools
        result = await self._send_request("tools/list", {})
        self._tools = result.get("tools", [])

    async def _send_request(self, method: str, params: dict) -> Any:
        self._request_id += 1
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        })
        assert self.process and self.process.stdin
        self.process.stdin.write(req + "\n")
        self.process.stdin.flush()
        # Read response
        assert self.process.stdout
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise EOFError("MCP server closed")
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                continue
            if resp.get("id") == self._request_id:
                if "error" in resp:
                    raise RuntimeError(f"MCP error: {resp['error']}")
                return resp.get("result", {})

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        # Extract text content from result
        content = result.get("content", [])
        texts = []
        for item in content:
            if item.get("type") == "text":
                texts.append(item["text"])
        return "\n".join(texts)

    def list_tools(self) -> list[dict]:
        return self._tools

    async def close(self) -> None:
        if self.process:
            self.process.stdin.close()
            self.process.wait(timeout=5)
            self.process = None


def get_memory_client(memory_path: str) -> MCPClient:
    """Create an MCP client connected to mcp-server-memory."""
    node_bin = shutil.which("mcp-server-memory")
    if not node_bin:
        # Try nvm path
        nvm_bin = os.path.expanduser("~/.nvm/versions/node/v20.20.2/bin/mcp-server-memory")
        if os.path.exists(nvm_bin):
            node_bin = nvm_bin
        else:
            raise FileNotFoundError(
                "mcp-server-memory not found. Install with: npm install -g @modelcontextprotocol/server-memory"
            )
    return MCPClient(
        [node_bin],
        env={"MEMORY_FILE_PATH": memory_path},
    )


def get_unified_history_client(config_path: str | None = None) -> MCPClient:
    """Create an MCP client connected to unified-history-mcp."""
    return MCPClient(
        [sys.executable, "-m", "unified_history_mcp.server"],
        env={"UNIFIED_HISTORY_CONFIG": config_path or ""} if config_path else {},
    )
