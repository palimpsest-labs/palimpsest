"""Agent loop for Palimpsest — the core investigative engine.

Talks to any OpenAI-compatible endpoint (ds4-server, llama.cpp server, Ollama, etc.)
and orchestrates the investigation through tool calling and methodology gates.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .case import get_case_dir, get_memory_path
from .gates import build_system_prompt, check_dossier_ready
from .state import load_state, save_state
from .tools import (
    get_all_tool_definitions,
    run_research_tool,
    ToolResult,
    MEMORY_TOOLS,
    RESEARCH_TOOLS,
)


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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, user_message: str | None = None) -> None:
        """One-shot: run one user message through the agent and exit."""
        self._print_status()
        if user_message:
            await self._run_turn(user_message)
        self._save()

    async def repl(self) -> None:
        """Interactive REPL: conversation loop with /commands."""
        self._print_status()
        if not self._has_saved_messages():
            print("\nWhat would you like to investigate?")
        else:
            print("\nResuming investigation. Type /help for commands.")

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
                self._handle_command(user_input)
                continue

            # Run the turn
            try:
                await self._run_turn(user_input)
            except RuntimeError as e:
                print(f"\n⚠️  Error: {e}")
            except KeyboardInterrupt:
                print("\n⏸️  Interrupted. Saving state...")
                self._save()

    async def run_turn_only(self, user_message: str) -> str:
        """Run one turn, return the model's final text response. Used by web UI."""
        await self._run_turn(user_message)
        # Return the last assistant content
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                return msg["content"]
        return ""

    # ------------------------------------------------------------------
    # Inner turn execution
    # ------------------------------------------------------------------

    async def _run_turn(self, user_message: str) -> None:
        """Run one user turn through the agent loop."""
        self.messages.append({"role": "user", "content": user_message})
        tools = get_all_tool_definitions()

        turn = 0
        max_turns = 50
        while turn < max_turns:
            turn += 1

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

            # Display content
            if content:
                print(f"\n{content}")

            # No tool calls? Done.
            if not tool_calls:
                self._save()
                return

            # Execute tool calls
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    args = {}

                print(f"\n  🔧 {name}({json.dumps(args, default=str)[:120]})")

                result = await self._dispatch_tool(name, args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{turn}"),
                    "content": result.content[:8000],
                })

                if result.is_error:
                    print(f"    ⚠️  {result.content[:200]}")
                else:
                    preview = result.content[:150].replace("\n", " ")
                    print(f"    ✓ {preview}...")

        self._save()

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def _dispatch_tool(self, name: str, args: dict) -> ToolResult:
        """Dispatch a tool call to the appropriate handler."""
        if name in {t["name"] for t in MEMORY_TOOLS}:
            return ToolResult(
                f"Memory tool '{name}' called with {json.dumps(args, default=str)}.\n"
                f"[MCP integration pending — graph ops applied via memory.jsonl directly.]",
                metadata={"tool": name, "args": args},
            )

        if name in {t["name"] for t in RESEARCH_TOOLS}:
            return run_research_tool(name, args, self.case_dir)

        return ToolResult(f"Unknown tool: {name}", is_error=True)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(self, messages: list[dict], tools: list[dict]) -> dict:
        """Call the LLM API."""
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

    def _handle_command(self, cmd: str) -> None:
        parts = cmd.split(maxsplit=1)
        name = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if name in ("/quit", "/q"):
            self._save()
            print("Saved. Goodbye.")
            sys.exit(0)

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

    def _save(self) -> None:
        """Persist messages and timestamp to state.json."""
        state = load_state(self.case_dir)
        state["agent_messages"] = self.messages
        state["last_action"] = datetime.now(timezone.utc).isoformat()
        save_state(self.case_dir, state)
