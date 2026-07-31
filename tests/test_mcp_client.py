"""Tests for MCP client lifecycle, error handling, and binary resolution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from palimpsest.mcp_client import (
    MCPClient,
    _resolve_memory_bin,
    get_memory_client,
    get_unified_history_client,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Mocks for the mcp SDK
# ---------------------------------------------------------------------------

def _make_mock_session(tool_names=("search_nodes", "create_entities")):
    """Return a mock session that acts as an async context manager."""
    from mcp.types import Tool, CallToolResult, TextContent

    session = MagicMock()
    # Make it act as an async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock()

    # Build the ListToolsResult dynamically
    ltr = type("ListToolsResult", (), {
        "tools": [Tool(name=n, description=f"Mock {n}", inputSchema={})
                  for n in tool_names]
    })()
    session.list_tools.return_value = ltr

    session.call_tool = AsyncMock()
    def _fake_call(name, arguments):
        return CallToolResult(
            content=[TextContent(type="text", text=f"result from {name}")],
            isError=False,
        )
    session.call_tool.side_effect = _fake_call
    return session


@pytest.fixture
def mock_stdio():
    """Patch stdio_client to return fake read/write streams."""
    with patch("palimpsest.mcp_client.stdio_client") as mock:
        fake_read = AsyncMock()
        fake_write = AsyncMock()
        # Simulate the context-manager enter/exit
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=(fake_read, fake_write))
        cm.__aexit__ = AsyncMock(return_value=None)
        mock.return_value = cm
        yield mock


# ---------------------------------------------------------------------------
# MCPClient start / close / knows
# ---------------------------------------------------------------------------

class TestStartClose:
    async def test_start_discovers_tools(self, mock_stdio):
        with patch("palimpsest.mcp_client.ClientSession",
                   return_value=_make_mock_session(["a", "b"])):
            client = MCPClient(MagicMock())
            await client.start()
            assert client.knows("a") is True
            assert client.knows("b") is True
            assert client.knows("missing") is False

    async def test_close_cleans_up(self, mock_stdio):
        with patch("palimpsest.mcp_client.ClientSession",
                   return_value=_make_mock_session()):
            client = MCPClient(MagicMock())
            await client.start()
            await client.close()
            assert client._stack is None
            assert client._session is None

    async def test_close_idempotent(self, mock_stdio):
        """Closing twice should not raise."""
        with patch("palimpsest.mcp_client.ClientSession",
                   return_value=_make_mock_session()):
            client = MCPClient(MagicMock())
            await client.start()
            await client.close()
            await client.close()  # second close is a no-op

    async def test_close_before_start_is_noop(self):
        client = MCPClient(MagicMock())
        await client.close()  # should not raise

    async def test_start_failure_cleans_up(self, mock_stdio):
        """If stdio_client raises after the AsyncExitStack is created,
        the stack is aclosed."""
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=RuntimeError("boom"))
        mock_stdio.return_value = cm

        client = MCPClient(MagicMock())
        with pytest.raises(RuntimeError, match="boom"):
            await client.start()

        assert client._stack is None
        assert client._session is None
        assert client._tool_names == frozenset()


# ---------------------------------------------------------------------------
# call_tool — isError propagation, timeout, empty content
# ---------------------------------------------------------------------------

class TestCallTool:
    async def test_success_returns_text(self, mock_stdio):
        with patch("palimpsest.mcp_client.ClientSession",
                   return_value=_make_mock_session(["search"])):
            client = MCPClient(MagicMock())
            await client.start()
            text, is_error = await client.call_tool("search", {"q": "x"})
            assert "result from search" in text
            assert is_error is False

    async def test_isError_propagated(self, mock_stdio):
        from mcp.types import CallToolResult, TextContent

        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        session.initialize = AsyncMock()
        session.list_tools = AsyncMock()
        session.list_tools.return_value = type("LTR", (), {"tools": []})()
        session.call_tool = AsyncMock()
        session.call_tool.return_value = CallToolResult(
            content=[TextContent(type="text", text="explosion")],
            isError=True,
        )

        with patch("palimpsest.mcp_client.ClientSession",
                   return_value=session):
            client = MCPClient(MagicMock())
            await client.start()
            text, is_error = await client.call_tool("boom", {})
            assert is_error is True
            assert "explosion" in text

    async def test_empty_content_diagnostic(self, mock_stdio):
        from mcp.types import CallToolResult

        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        session.initialize = AsyncMock()
        session.list_tools = AsyncMock()
        session.list_tools.return_value = type("LTR", (), {"tools": []})()
        session.call_tool = AsyncMock()
        session.call_tool.return_value = CallToolResult(
            content=[], isError=False,
        )

        with patch("palimpsest.mcp_client.ClientSession",
                   return_value=session):
            client = MCPClient(MagicMock())
            await client.start()
            text, is_error = await client.call_tool("silent", {})
            assert "no text content" in text
            assert is_error is False  # empty is not an error per se

    async def test_empty_with_isError(self, mock_stdio):
        from mcp.types import CallToolResult

        session = AsyncMock()
        session.initialize = AsyncMock()
        session.list_tools.return_value = type("LTR", (), {"tools": []})()
        session.call_tool.return_value = CallToolResult(
            content=[], isError=True,
        )

        with patch("palimpsest.mcp_client.ClientSession",
                   return_value=session):
            client = MCPClient(MagicMock())
            await client.start()
            text, is_error = await client.call_tool("boom", {})
            assert "server error" in text
            assert is_error is True

    async def test_call_tool_before_start_raises(self):
        client = MCPClient(MagicMock())
        with pytest.raises(RuntimeError, match="not started"):
            await client.call_tool("x", {})


# ---------------------------------------------------------------------------
# Binary resolution
# ---------------------------------------------------------------------------

class TestBinaryResolution:
    def test_resolves_memory_mcp_first(self):
        """memory-mcp should be the first candidate tried."""
        with patch("palimpsest.mcp_client.shutil.which") as which:
            which.side_effect = lambda name: (
                "/usr/local/bin/memory-mcp" if name == "memory-mcp" else None
            )
            with patch("palimpsest.mcp_client.os.path.exists",
                       return_value=True):
                path = _resolve_memory_bin()
                assert "memory-mcp" in path

    def test_falls_back_to_mcp_server_memory(self):
        """If memory-mcp is absent, try mcp-server-memory."""
        with patch("palimpsest.mcp_client.shutil.which") as which:
            which.side_effect = lambda name: (
                "/usr/local/bin/mcp-server-memory"
                if name == "mcp-server-memory" else None
            )
            def exists(path):
                return "mcp-server-memory" in str(path)
            with patch("palimpsest.mcp_client.os.path.exists",
                       side_effect=exists):
                path = _resolve_memory_bin()
                assert "mcp-server-memory" in path

    def test_raises_when_none_found(self):
        with patch("palimpsest.mcp_client.shutil.which", return_value=None):
            with patch("palimpsest.mcp_client.os.path.exists",
                       return_value=False):
                with pytest.raises(FileNotFoundError, match="memory-mcp"):
                    _resolve_memory_bin()


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

class TestFactories:
    def test_get_memory_client_sets_env(self):
        with patch("palimpsest.mcp_client._resolve_memory_bin",
                   return_value="/bin/memory-mcp"):
            client = get_memory_client("/tmp/test-case/memory.jsonl")
            assert client._params.env["MEMORY_FILE_PATH"] == (
                "/tmp/test-case/memory.jsonl"
            )

    def test_get_unified_history_client(self):
        client = get_unified_history_client("/tmp/config.yaml")
        assert client._params.command.endswith("python") or "python" in str(
            client._params.command
        )
        assert client._params.env["UNIFIED_HISTORY_CONFIG"] == "/tmp/config.yaml"
