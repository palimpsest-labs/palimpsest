"""Tests for Agent MCP integration, dispatch, and lifecycle."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from palimpsest.agent import Agent, _MEMORY_TOOL_NAMES, _RESEARCH_TOOL_NAMES
from palimpsest.case import create_case
from palimpsest.tools import ToolResult

pytestmark = pytest.mark.asyncio


@pytest.fixture
def case_dir():
    """Create a temporary case and return its (slug, base_dir)."""
    with tempfile.TemporaryDirectory() as td:
        slug = "test-agent-case"
        create_case(slug, base_dir=td)
        yield slug, td


@pytest.fixture
def agent(case_dir):
    """Return an Agent pointed at a temporary case."""
    slug, base_dir = case_dir
    from palimpsest.case import _resolve_base
    case_path = _resolve_base(base_dir) / slug

    # Patch case resolution so the agent and _ensure_mcp both use temp dirs
    with patch("palimpsest.agent.get_case_dir", return_value=case_path), \
         patch("palimpsest.agent.get_memory_path",
               return_value=case_path / "memory.jsonl"):
        agent = Agent(slug)
        agent.case_dir = case_path
        # Reload state from the temp case
        from palimpsest.state import load_state
        from palimpsest.gates import build_system_prompt
        state = load_state(agent.case_dir)
        system_prompt = build_system_prompt(agent.case_dir)
        agent.messages = [{"role": "system", "content": system_prompt}]
        saved = state.get("agent_messages", [])
        if saved:
            agent.messages.extend(saved)
        yield agent


# ---------------------------------------------------------------------------
# Tool name sets
# ---------------------------------------------------------------------------

class TestToolNames:
    def test_all_memory_tools_have_prefix(self):
        for name in _MEMORY_TOOL_NAMES:
            assert name.startswith("memory_"), f"Bad name: {name}"

    def test_mcp_name_mapping(self):
        """Stripping 'memory_' prefix gives valid MCP tool names."""
        for name in _MEMORY_TOOL_NAMES:
            mcp_name = name.removeprefix("memory_")
            assert mcp_name, f"Empty MCP name for {name}"
            assert mcp_name != name, f"Prefix not stripped: {name}"

    def test_memory_tools_are_12(self):
        assert len(_MEMORY_TOOL_NAMES) == 12

    def test_research_tools_are_4(self):
        assert len(_RESEARCH_TOOL_NAMES) == 4


# ---------------------------------------------------------------------------
# _ensure_mcp
# ---------------------------------------------------------------------------

class TestEnsureMCP:
    async def test_returns_none_when_binary_missing(self, agent):
        """When memory-mcp is not on PATH, _ensure_mcp returns None."""
        with patch("palimpsest.agent.get_memory_client",
                   side_effect=FileNotFoundError("no binary")):
            client = await agent._ensure_mcp()
            assert client is None
            assert agent._memory_client is None

    async def test_retries_after_failure(self, agent):
        """_ensure_mcp should try again each call — no permanent error cache."""
        call_count = [0]

        def failing_then_ok(_):
            call_count[0] += 1
            if call_count[0] == 1:
                raise FileNotFoundError("first fail")
            mock = MagicMock()
            mock.start = AsyncMock()
            mock.knows = MagicMock(return_value=True)
            mock.call_tool = AsyncMock(return_value=("ok", False))
            mock.close = AsyncMock()
            return mock

        with patch("palimpsest.agent.get_memory_client",
                   side_effect=failing_then_ok):
            # First call fails
            client1 = await agent._ensure_mcp()
            assert client1 is None

            # Second call should retry and succeed
            client2 = await agent._ensure_mcp()
            assert client2 is not None
            assert call_count[0] == 2

    async def test_cleans_up_partial_client_on_failure(self, agent):
        """If get_memory_client succeeds but start() fails, the client is closed."""
        mock_client = MagicMock()
        mock_client.start = AsyncMock(side_effect=RuntimeError("start fail"))
        mock_client.close = AsyncMock()

        with patch("palimpsest.agent.get_memory_client",
                   return_value=mock_client):
            client = await agent._ensure_mcp()
            assert client is None
            assert agent._memory_client is None
            mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# _dispatch_tool
# ---------------------------------------------------------------------------

class TestDispatchTool:
    async def test_memory_tool_success(self, agent):
        """A successful memory tool call returns is_error=False."""
        mock_client = MagicMock()
        mock_client.knows = MagicMock(return_value=True)
        mock_client.call_tool = AsyncMock(return_value=("found entity", False))

        with patch.object(agent, "_ensure_mcp",
                          AsyncMock(return_value=mock_client)):
            result = await agent._dispatch_tool(
                "memory_search_nodes", {"query": "test"}
            )
            assert isinstance(result, ToolResult)
            assert result.is_error is False
            assert "found entity" in result.content

    async def test_memory_tool_isError_propagated(self, agent):
        """When call_tool returns is_error=True, ToolResult gets it."""
        mock_client = MagicMock()
        mock_client.knows = MagicMock(return_value=True)
        mock_client.call_tool = AsyncMock(return_value=("explosion", True))

        with patch.object(agent, "_ensure_mcp",
                          AsyncMock(return_value=mock_client)):
            result = await agent._dispatch_tool(
                "memory_delete_entities", {"entityNames": ["x"]}
            )
            assert result.is_error is True
            assert "explosion" in result.content

    async def test_memory_tool_unknown_to_server(self, agent):
        """When the server doesn't know the tool, return an error."""
        mock_client = MagicMock()
        mock_client.knows = MagicMock(return_value=False)

        with patch.object(agent, "_ensure_mcp",
                          AsyncMock(return_value=mock_client)):
            result = await agent._dispatch_tool(
                "memory_traverse", {"start_node": "x"}
            )
            assert result.is_error is True
            assert "not supported" in result.content

    async def test_memory_tool_no_client(self, agent):
        """When MCP is unavailable, return a clear error."""
        with patch.object(agent, "_ensure_mcp",
                          AsyncMock(return_value=None)):
            result = await agent._dispatch_tool(
                "memory_search_nodes", {"query": "x"}
            )
            assert result.is_error is True
            assert "unavailable" in result.content.lower()

    async def test_memory_tool_failure_resets_client(self, agent):
        """When call_tool raises, the client is reset so next call re-inits."""
        mock_client = MagicMock()
        mock_client.knows = MagicMock(return_value=True)
        mock_client.call_tool = AsyncMock(side_effect=RuntimeError("wire broken"))

        with patch.object(agent, "_ensure_mcp",
                          AsyncMock(return_value=mock_client)):
            result = await agent._dispatch_tool(
                "memory_search_nodes", {"query": "x"}
            )
            assert result.is_error is True
            assert "wire broken" in result.content

        # Agent's MCP client should have been torn down
        assert agent._memory_client is None

    async def test_research_tool_routed(self, agent):
        """Research tools go to run_research_tool."""
        with patch("palimpsest.agent.run_research_tool") as mock_run:
            mock_run.return_value = ToolResult("companies house result")
            result = await agent._dispatch_tool(
                "companies_house_lookup", {"company_number": "123"}
            )
            mock_run.assert_called_once()
            assert result.content == "companies house result"

    async def test_unknown_tool_is_error(self, agent):
        result = await agent._dispatch_tool("bogus_tool", {})
        assert result.is_error is True
        assert "Unknown tool" in result.content


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestClose:
    async def test_close_idempotent(self, agent):
        """Calling close twice should not raise."""
        await agent.close()
        await agent.close()

    async def test_close_no_client(self, agent):
        """close() when no MCP client was ever started is a no-op."""
        await agent.close()
        assert agent._memory_client is None


# ---------------------------------------------------------------------------
# _handle_command
# ---------------------------------------------------------------------------

class TestHandleCommand:
    def test_quit_returns_true(self, agent):
        assert agent._handle_command("/quit") is True
        assert agent._handle_command("/q") is True

    @pytest.mark.parametrize("cmd", [
        "/save", "/phase", "/leads", "/hypothesis", "/status", "/help",
        "/phase-set map", "/unknown",
    ])
    def test_other_commands_return_false(self, agent, cmd):
        assert agent._handle_command(cmd) is False
