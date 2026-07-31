"""Agent loop for Palimpsest — the core investigative engine.

Talks to any OpenAI-compatible endpoint (ds4-server, llama.cpp server, Ollama, etc.)
and orchestrates the investigation through tool calling and methodology gates.
"""

from __future__ import annotations

import asyncio
import http.client
import json
import os
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

from .case import get_case_dir, get_memory_path
from .gates import build_system_prompt
from .mcp_client import MCPClient, get_memory_client
from .state import load_state, save_state
from .tools import (
    get_all_tool_definitions,
    run_research_tool,
    ToolResult,
    MEMORY_TOOLS,
    RESEARCH_TOOLS,
)

# Pre-built frozenset for O(1) membership tests
_MEMORY_TOOL_NAMES = frozenset(t["name"] for t in MEMORY_TOOLS)
_RESEARCH_TOOL_NAMES = frozenset(t["name"] for t in RESEARCH_TOOLS)


# ------------------------------------------------------------------
# Turn events — decouple agent output from presentation layer
# ------------------------------------------------------------------

@dataclass
class TextEvent:
    """Assistant text content, possibly mid-stream."""
    content: str
    is_streaming: bool = False  # True for partial deltas, False for complete


@dataclass
class ToolCallEvent:
    """A tool invocation has started."""
    name: str
    args: dict
    call_id: str


@dataclass
class ToolResultEvent:
    """A tool call returned a result."""
    call_id: str
    name: str
    content: str
    is_error: bool = False


@dataclass
class TurnCompleteEvent:
    """The turn finished, with optional final text."""
    final_text: str = ""


# Union type for any event the agent can emit
AgentEvent = TextEvent | ToolCallEvent | ToolResultEvent | TurnCompleteEvent

# Callback signature: async or sync, receives an AgentEvent
EventCallback = Callable[[AgentEvent], Any]


# Default LLM endpoint — configurable via env
DEFAULT_BASE_URL = os.environ.get("PALIMPSEST_LLM_URL", "http://127.0.0.1:8000/v1")
DEFAULT_MODEL = os.environ.get("PALIMPSEST_MODEL", "deepseek-v4-flash")
DEFAULT_API_KEY = os.environ.get("PALIMPSEST_API_KEY", "dsv4-local")


class Agent:
    """Investigative agent that runs the methodology loop."""

    def __init__(self, slug: str):
        self.slug = slug
        self.case_dir = get_case_dir(slug)
        self.base_url = DEFAULT_BASE_URL.rstrip("/")
        self.model = DEFAULT_MODEL
        self.api_key = DEFAULT_API_KEY

        # Build message history from saved state
        state = load_state(self.case_dir)
        system_prompt = build_system_prompt(self.case_dir)
        self.messages: list[dict] = [{"role": "system", "content": system_prompt}]
        saved = state.get("agent_messages", [])
        if saved:
            self.messages.extend(saved)

        # MCP memory client — started lazily on first memory tool call
        self._memory_client: MCPClient | None = None

    async def _ensure_mcp(self) -> MCPClient | None:
        """Lazily start the memory MCP client. Returns None if unavailable."""
        if self._memory_client is not None:
            return self._memory_client
        try:
            memory_path = str(get_memory_path(self.slug))
            self._memory_client = get_memory_client(memory_path)
            await self._memory_client.start()
        except (FileNotFoundError, RuntimeError, EOFError, OSError) as e:
            if self._memory_client is not None:
                try:
                    await self._memory_client.close()
                except Exception:
                    pass
                self._memory_client = None
            print(f"  ⚠️  MCP memory unavailable: {e}", file=sys.stderr)
            return None
        return self._memory_client

    async def close(self) -> None:
        """Shut down the MCP memory client."""
        if self._memory_client is not None:
            try:
                await self._memory_client.close()
            except Exception:
                import traceback
                traceback.print_exc(file=sys.stderr)
            self._memory_client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, user_message: str | None = None) -> None:
        """One-shot: run one user message through the agent and exit."""
        try:
            self._print_status()
            if user_message:
                await self._run_turn(user_message, on_event=_cli_print_event)
            self._save()
        finally:
            await self.close()

    async def repl(self) -> None:
        """Interactive REPL: conversation loop with /commands."""
        self._print_status()
        if not self._has_saved_messages():
            print("\nWhat would you like to investigate?")
        else:
            print("\nResuming investigation. Type /help for commands.")

        try:
            while True:
                try:
                    user_input = input("\n▸ ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nSaving...")
                    self._save()
                    break

                if not user_input:
                    continue

                # Handle /commands
                if user_input.startswith("/"):
                    if self._handle_command(user_input):
                        break
                    continue

                # Run the turn
                try:
                    await self._run_turn(user_input, on_event=_cli_print_event)
                except RuntimeError as e:
                    print(f"\n⚠️  Error: {e}")
                except KeyboardInterrupt:
                    print("\n⏸️  Interrupted. Saving state...")
                    self._save()
                    # Reset MCP client — it may be in an indeterminate state
                    await self.close()
        finally:
            await self.close()

    async def run_turn(self, user_message: str,
                       on_event: EventCallback | None = None) -> str:
        """Run one turn, return the model's final text response.

        If *on_event* is provided, it receives streaming text and tool
        notifications during the turn.  Used by the web UI for SSE streaming.
        """
        await self._run_turn(user_message, on_event=on_event)
        # Return the last assistant content
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                return msg["content"]
        return ""

    # ------------------------------------------------------------------
    # Inner turn execution
    # ------------------------------------------------------------------

    async def _run_turn(self, user_message: str,
                        on_event: EventCallback | None = None) -> None:
        """Run one user turn through the agent loop.

        If *on_event* is provided, it receives :class:`AgentEvent` instances
        for every observable event during the turn — text content, tool
        invocations, and tool results.  When *on_event* is ``None`` the turn
        runs silently (suitable for one-shot queries where only the final
        text matters).
        """
        self.messages.append({"role": "user", "content": user_message})
        tools = get_all_tool_definitions()

        turn = 0
        max_turns = 50
        while turn < max_turns:
            turn += 1

            if on_event is not None:
                # Streaming path — emits text deltas to the callback
                _used_streaming = True
                content, tool_calls = self._call_llm_stream(
                    self.messages, tools, on_event, turn_number=turn)
            else:
                # Non-streaming path (one-shot, no UI)
                _used_streaming = False
                response = self._call_llm(self.messages, tools)
                choice = response.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                tool_calls = message.get("tool_calls", [])

            # Record assistant message
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self.messages.append(assistant_msg)

            # Emit text content (only for non-streaming — streaming already sent deltas)
            if content and on_event and not _used_streaming:
                on_event(TextEvent(content))

            # No tool calls? Done.
            if not tool_calls:
                self._save()
                if on_event:
                    on_event(TurnCompleteEvent(final_text=content or ""))
                return

            # Execute tool calls
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                call_id = tc.get("id", f"call_{turn}")
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    args = {}

                if on_event:
                    on_event(ToolCallEvent(name=name, args=args, call_id=call_id))

                result = await self._dispatch_tool(name, args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result.content[:8000],
                })

                if on_event:
                    on_event(ToolResultEvent(
                        call_id=call_id,
                        name=name,
                        content=result.content[:200],
                        is_error=result.is_error,
                    ))

        self._save()

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def _dispatch_tool(self, name: str, args: dict) -> ToolResult:
        """Dispatch a tool call to the appropriate handler."""
        if name in _MEMORY_TOOL_NAMES:
            mcp_name = name.removeprefix("memory_")
            client = await self._ensure_mcp()
            if client is None:
                return ToolResult(
                    f"Memory tool '{name}' unavailable: memory-mcp server is not installed or "
                    f"not on PATH.\nInstall memory-mcp from the palimpsest-labs toolkit.",
                    is_error=True,
                    metadata={"tool": name},
                )
            if not client.knows(mcp_name):
                return ToolResult(
                    f"Memory tool '{name}' not supported by the connected memory server "
                    f"(server reports these tools: {sorted(client._tool_names)})",
                    is_error=True,
                    metadata={"tool": name},
                )
            try:
                result_text, is_error = await client.call_tool(mcp_name, args)
                return ToolResult(
                    result_text,
                    is_error=is_error,
                    metadata={"tool": name, "args": args},
                )
            except (RuntimeError, EOFError, OSError, asyncio.TimeoutError) as e:
                # Tear down the possibly-corrupt client so next call re-initialises
                await self.close()
                return ToolResult(
                    f"Memory tool '{name}' failed: {e}",
                    is_error=True,
                    metadata={"tool": name, "error": str(e)},
                )

        if name in _RESEARCH_TOOL_NAMES:
            return run_research_tool(name, args, self.case_dir)

        return ToolResult(f"Unknown tool: {name}", is_error=True)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(self, messages: list[dict], tools: list[dict]) -> dict:
        """Call the LLM API (non-streaming)."""
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "temperature": 0.0,
            "max_tokens": 4096,
        }).encode("utf-8")

        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API error {e.code}: {body[:500]}")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot connect to LLM at {self.base_url}. "
                f"Is ds4-server running? ({e})"
            )

    def _call_llm_stream(
        self, messages: list[dict], tools: list[dict],
        on_event: EventCallback, turn_number: int = 0,
    ) -> tuple[str, list[dict]]:
        """Call the LLM API with ``stream: true``, emitting text deltas.

        Accumulates tool-call fragments across streaming chunks and returns
        ``(accumulated_content, tool_calls)`` when the stream completes.
        This is intentionally synchronous — the calling async loop handles
        yield points between turns, not mid-stream.
        """
        parsed = urlparse(self.base_url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        timeout = 300

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "temperature": 0.0,
            "max_tokens": 4096,
            "stream": True,
        }).encode("utf-8")

        if parsed.scheme == "https":
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                parsed.hostname, port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(
                parsed.hostname, port, timeout=timeout)

        try:
            conn.request(
                "POST", f"{parsed.path}/chat/completions",
                body=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            resp = conn.getresponse()
            if resp.status != 200:
                body = resp.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"LLM API error {resp.status}: {body[:500]}")

            accumulated_content = ""
            tool_calls_acc: dict[int, dict[str, Any]] = {}
            raw_buffer = b""

            while True:
                chunk = resp.read(256)
                if not chunk:
                    break
                raw_buffer += chunk

                # Decode what we can — keep incomplete multi-byte sequences
                try:
                    text = raw_buffer.decode("utf-8")
                except UnicodeDecodeError as e:
                    # Split at the last complete character
                    text = raw_buffer[:e.start].decode("utf-8")
                    raw_buffer = raw_buffer[e.start:]
                else:
                    raw_buffer = b""

                for line in text.split("\n"):
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    choices = event.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})

                    # Content deltas
                    txt = delta.get("content", "")
                    if txt:
                        accumulated_content += txt
                        on_event(TextEvent(content=txt, is_streaming=True))

                    # Tool-call fragment accumulation
                    for tc in delta.get("tool_calls", []):
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        entry = tool_calls_acc[idx]
                        if tc.get("id"):
                            entry["id"] = tc["id"]
                        func = tc.get("function", {})
                        if func.get("name"):
                            entry["function"]["name"] += func["name"]
                        if "arguments" in func:
                            entry["function"]["arguments"] += func.get(
                                "arguments", "")

            # Fill any missing tool-call IDs with synthetic values
            tool_calls = []
            for idx, tc in tool_calls_acc.items():
                if not tc["id"]:
                    tc["id"] = f"call_{turn_number}_{idx}"
                tool_calls.append(tc)
        finally:
            conn.close()

        tool_calls = list(tool_calls_acc.values()) if tool_calls_acc else []
        return accumulated_content, tool_calls

    # ------------------------------------------------------------------
    # REPL helpers
    # ------------------------------------------------------------------

    def _print_status(self) -> None:
        state = load_state(self.case_dir)
        title = state.get("title", self.slug)
        phase = state.get("phase", "scope")
        leads = len(state.get("open_leads", []))
        hypothesis = state.get("working_hypothesis")

        print(f"╭─ Case: {title}")
        print(f"├─ Phase: {phase}  │  Open leads: {leads}")
        if hypothesis:
            print(f"├─ Hypothesis: {hypothesis[:100]}")
        print(f"╰─ Type /help for commands")

    def _has_saved_messages(self) -> bool:
        state = load_state(self.case_dir)
        return bool(state.get("agent_messages"))

    def _handle_command(self, cmd: str) -> bool:
        """Handle a REPL /command. Returns True if the REPL should exit."""
        parts = cmd.split(maxsplit=1)
        name = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if name in ("/quit", "/q"):
            self._save()
            print("Saved. Goodbye.")
            return True

        elif name == "/save":
            self._save()
            print("State saved.")

        elif name == "/phase":
            state = load_state(self.case_dir)
            print(f"Current phase: {state.get('phase', 'scope')}")
            print(f"Phase order: scope → map → enumerate → corroborate → synthesize → gap_analysis → report")

        elif name == "/leads":
            state = load_state(self.case_dir)
            leads = state.get("open_leads", [])
            if leads:
                print(f"Open leads ({len(leads)}):")
                for i, lead in enumerate(leads, 1):
                    print(f"  {i}. {lead}")
            else:
                print("No open leads.")

        elif name == "/hypothesis":
            state = load_state(self.case_dir)
            h = state.get("working_hypothesis")
            if h:
                print(f"Working hypothesis: {h}")
            else:
                print("No working hypothesis yet.")

        elif name == "/status":
            self._print_status()

        elif name == "/phase-set" and arg:
            new_phase = arg.strip()
            from .gates import advance_phase
            if advance_phase(self.case_dir, new_phase):
                from .state import update_state
                update_state(self.case_dir, phase=new_phase)
                # Rebuild system prompt for phase change
                self.messages[0] = {"role": "system", "content": build_system_prompt(self.case_dir)}
                print(f"Phase advanced to: {new_phase}")
            else:
                print(f"Invalid phase: {new_phase}")
                print(f"Valid phases: scope, map, enumerate, corroborate, synthesize, gap_analysis, report")

        elif name == "/help":
            print("""Commands:
  /status       Show investigation overview
  /phase        Show current phase + phase order
  /leads        List open leads
  /hypothesis   Show working hypothesis
  /phase-set N  Advance to phase N (e.g., /phase-set enumerate)
  /save         Save current state
  /quit, /q     Save and exit
  /help         Show this help

Just type to talk to the agent.
Ctrl+C interrupts the current generation.
Ctrl+D quits (saves state).""")

        else:
            print(f"Unknown command: {name}. Type /help for commands.")

        return False

    def _save(self) -> None:
        """Persist messages and timestamp to state.json."""
        state = load_state(self.case_dir)
        state["agent_messages"] = self.messages
        state["last_action"] = datetime.now(timezone.utc).isoformat()
        save_state(self.case_dir, state)


# ------------------------------------------------------------------
# CLI event callback — restores the original print behaviour
# ------------------------------------------------------------------

def _cli_print_event(event: AgentEvent) -> None:
    """Print agent events to stdout for the CLI REPL."""
    if isinstance(event, TextEvent):
        print(f"\n{event.content}")
    elif isinstance(event, ToolCallEvent):
        print(f"\n  🔧 {event.name}({json.dumps(event.args, default=str)[:120]})")
    elif isinstance(event, ToolResultEvent):
        if event.is_error:
            print(f"    ⚠️  {event.content}")
        else:
            preview = event.content[:150].replace("\n", " ")
            print(f"    ✓ {preview}...")
    # TurnCompleteEvent is silent in CLI
