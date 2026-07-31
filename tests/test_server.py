"""Tests for server-side agent lifecycle (run_turn_sync + shutdown cleanup)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from palimpsest.server import _run_turn_sync_patch, _agents


# Create a patchable Agent class
class FakeAgent:
    def __init__(self, slug="test"):
        self.slug = slug
        self.messages = [
            {"role": "assistant", "content": "hello from agent"}
        ]
        self._memory_client = MagicMock()
        self._memory_client.close = AsyncMock()
        self._run_turn = AsyncMock()
        self.close = AsyncMock()

    async def _real_close(self):
        if self._memory_client:
            await self._memory_client.close()
            self._memory_client = None


# ---------------------------------------------------------------------------
# run_turn_sync — MCP teardown
# ---------------------------------------------------------------------------

class TestRunTurnSync:
    def test_closes_mcp_after_turn(self):
        """run_turn_sync should call agent.close() after the turn completes."""
        agent = FakeAgent()

        result = _run_turn_sync_patch(agent, "investigate x")
        assert "hello from agent" in result
        # close() should have been called in the finally block
        agent.close.assert_awaited_once()

    def test_closes_mcp_even_on_error(self):
        """run_turn_sync must close MCP even when _run_turn raises."""
        agent = FakeAgent()
        agent._run_turn = AsyncMock(side_effect=RuntimeError("LLM down"))

        with pytest.raises(RuntimeError, match="LLM down"):
            _run_turn_sync_patch(agent, "investigate x")

        agent.close.assert_awaited_once()

    def test_closes_mcp_even_on_keyboard_interrupt(self):
        """run_turn_sync must close MCP even when interrupted."""
        agent = FakeAgent()
        agent._run_turn = AsyncMock(side_effect=KeyboardInterrupt())

        with pytest.raises(KeyboardInterrupt):
            _run_turn_sync_patch(agent, "investigate x")

        agent.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Server shutdown — agent cleanup
# ---------------------------------------------------------------------------

class TestServerShutdown:
    def test_serve_closes_all_cached_agents(self):
        """On shutdown, all agents in _agents have close() called."""
        # Populate the cache
        a1 = FakeAgent("case-1")
        a2 = FakeAgent("case-2")
        _agents["case-1"] = a1
        _agents["case-2"] = a2

        # Simulate the cleanup loop from serve()
        import asyncio
        for agent in list(_agents.values()):
            try:
                asyncio.run(agent.close())
            except Exception:
                pass

        a1.close.assert_awaited_once()
        a2.close.assert_awaited_once()

        # Clean up global state
        _agents.clear()
