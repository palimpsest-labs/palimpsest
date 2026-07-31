"""HTTP server for the Palimpsest web interface.

``palimpsest serve`` starts a :class:`ThreadingHTTPServer` on localhost
and opens the single-page web UI in a browser tab.  All auth / security
is handled by binding to ``127.0.0.1`` — this is a local-first tool for
sensitive investigations and should never be exposed on a network.

API
---

===== ====== =========================================
Method Path   Description
===== ====== =========================================
GET   /       Single-page web UI
GET   /api/cases
              List all cases
GET   /api/cases/<slug>/state
              Case state (phase, leads, hypothesis …)
GET   /api/cases/<slug>/history
              Chat history (transformed for frontend)
GET   /api/cases/<slug>/evidence
              Evidence manifest entries
GET   /api/cases/<slug>/dossier
              Dossier content (template with filled state)
POST  /api/cases/<slug>/chat
              Streaming chat — SSE response with typed events
GET   /api/cases/<slug>/captures/<file>
              Serve a capture file by name
GET   /vendor/<file>
              Vendored JS/CSS assets
===== ====== =========================================
"""

from __future__ import annotations

import json
import os
import re
import signal
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from .agent import (
    Agent, AgentEvent, TextEvent, ToolCallEvent,
    ToolResultEvent, TurnCompleteEvent,
)
from .case import get_case_dir, list_cases
from .state import load_state, save_state

DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"

# Route pattern: /api/cases/<slug>/<resource>
_ROUTE_RE = re.compile(r"^/api/cases/([a-z0-9]+(?:-[a-z0-9]+)*)(?:/(.*))?$")


# ------------------------------------------------------------------
# Atomic state persistence
# ------------------------------------------------------------------

def _atomic_save_state(case_dir: Path, state: dict[str, Any]) -> None:
    """Save state.json atomically — write to temp file, then rename."""
    tmp = case_dir / ".state.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)
    os.replace(tmp, case_dir / "state.json")


# ------------------------------------------------------------------
# Request handler
# ------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    """HTTP request handler with route dispatch."""

    # Silence per-request log lines
    def log_message(self, fmt: str, *args: Any) -> None:
        pass

    # ------------------------------------------------------------------
    # Route dispatch
    # ------------------------------------------------------------------

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # Static assets
        if path == "/":
            return self._serve_html()
        if path.startswith("/vendor/"):
            return self._serve_vendor(path[8:])

        # API: case list
        if path == "/api/cases":
            return self._json(list_cases())

        # API: case-scoped routes
        m = _ROUTE_RE.match(path)
        if m:
            slug = m.group(1)
            resource = m.group(2) or ""
            return self._handle_case_get(slug, resource)

        self._error(404, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        m = _ROUTE_RE.match(path)
        if m and m.group(2) == "chat":
            return self._handle_chat_post(m.group(1))

        self._error(404, "Not found")

    # ------------------------------------------------------------------
    # Case-scoped GETs
    # ------------------------------------------------------------------

    def _handle_case_get(self, slug: str, resource: str) -> None:
        try:
            case_dir = get_case_dir(slug)
        except FileNotFoundError:
            return self._error(404, f"Case {slug!r} not found")

        if resource == "state":
            return self._case_state(case_dir)
        if resource == "history":
            return self._case_history(case_dir)
        if resource == "evidence":
            return self._case_evidence(case_dir)
        if resource == "dossier":
            return self._case_dossier(case_dir)
        if resource.startswith("captures/"):
            filename = resource[len("captures/"):]
            return self._serve_capture(case_dir, filename)

        self._error(404, f"Unknown resource: {resource}")

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------

    def _case_state(self, case_dir: Path) -> None:
        state = load_state(case_dir)
        self._json({
            "slug": state.get("slug"),
            "title": state.get("title"),
            "phase": state.get("phase", "scope"),
            "open_leads": state.get("open_leads", []),
            "working_hypothesis": state.get("working_hypothesis"),
            "created": state.get("created"),
            "updated": state.get("updated"),
        })

    def _case_history(self, case_dir: Path) -> None:
        """Return chat history transformed for the frontend.

        Converts raw OpenAI-format messages (system/user/assistant/tool)
        into a simpler array of {role, content, tool_calls?, tool_results?}.
        """
        state = load_state(case_dir)
        raw = state.get("agent_messages", [])
        history: list[dict[str, Any]] = []

        for msg in raw:
            role = msg.get("role", "")
            if role == "system":
                continue  # frontend doesn't display the system prompt
            entry: dict[str, Any] = {"role": role}
            if msg.get("content"):
                entry["content"] = msg["content"]
            if msg.get("tool_calls"):
                entry["tool_calls"] = [
                    {
                        "id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", ""),
                        "args": tc.get("function", {}).get("arguments", ""),
                    }
                    for tc in msg["tool_calls"]
                ]
            if role == "tool":
                entry["tool_call_id"] = msg.get("tool_call_id", "")
                # Truncate long tool results for display
                content = msg.get("content", "")
                if len(content) > 500:
                    entry["content"] = content[:500] + "…"
                else:
                    entry["content"] = content
            history.append(entry)

        self._json(history)

    def _case_evidence(self, case_dir: Path) -> None:
        manifest_path = case_dir / "captures" / "manifest.jsonl"
        entries: list[dict[str, Any]] = []
        if manifest_path.is_file():
            for line in manifest_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        self._json(entries)

    def _case_dossier(self, case_dir: Path) -> None:
        """Return dossier content — template filled with state data."""
        state = load_state(case_dir)
        # Try to read existing dossier, fall back to rendering template
        dossier_file = case_dir / "dossier.md"
        if dossier_file.is_file():
            return self._serve_file(dossier_file, "text/markdown")

        # Render the template with available state
        import importlib.resources
        try:
            template = (
                importlib.resources.files("palimpsest.templates")
                .joinpath("dossier.md")
                .read_text(encoding="utf-8")
            )
        except Exception:
            template = "# {{TITLE}}\n\nNo dossier template found."

        title = state.get("title", state.get("slug", "Untitled"))
        phase = state.get("phase", "scope")
        hypothesis = state.get("working_hypothesis") or "Not yet formulated."
        leads = ", ".join(state.get("open_leads", [])) or "None"

        body = template.replace("{{TITLE}}", title)
        body = body.replace("{{PHASE}}", phase)
        body = body.replace("{{HYPOTHESIS}}", hypothesis)
        body = body.replace("{{LEADS}}", leads)

        self._text(body, "text/markdown")

    # ------------------------------------------------------------------
    # Streaming chat (POST)
    # ------------------------------------------------------------------

    def _handle_chat_post(self, slug: str) -> None:
        # Read request body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._error(400, "Invalid JSON")
        message = data.get("message", "")
        if not message:
            return self._error(400, "Missing 'message' field")

        try:
            case_dir = get_case_dir(slug)
        except FileNotFoundError:
            return self._error(404, f"Case {slug!r} not found")

        # SSE headers
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        # Per-case turn lock — one turn at a time
        lock = _get_case_lock(slug)
        if not lock.acquire(blocking=False):
            self._write_sse("error", {"message": "A turn is already in progress."})
            return

        # Capture self in closure for the callback
        handler = self

        try:
            agent = _get_agent(slug)

            def on_event(event: AgentEvent) -> None:
                """Write each event as an SSE frame immediately."""
                nonlocal handler
                if isinstance(event, TextEvent):
                    handler._write_sse("text_delta", {
                        "content": event.content,
                        "is_streaming": event.is_streaming,
                    })
                elif isinstance(event, ToolCallEvent):
                    handler._write_sse("tool_call", {
                        "name": event.name,
                        "args": event.args,
                        "call_id": event.call_id,
                    })
                elif isinstance(event, ToolResultEvent):
                    handler._write_sse("tool_result", {
                        "call_id": event.call_id,
                        "name": event.name,
                        "content": event.content[:500],
                        "is_error": event.is_error,
                    })

            final_text = agent.run_turn_sync(message, on_event=on_event)

            self._write_sse("turn_complete", {"final_text": final_text})
            self._write_sse("done", {})

            # Save state atomically
            state = load_state(case_dir)
            state["agent_messages"] = agent.messages
            _atomic_save_state(case_dir, state)
        except _ClientDisconnected:
            # Browser closed the connection — agent turn continues in
            # background but we stop writing frames.  State is saved by
            # the agent's own _save() calls during the turn.
            pass
        except Exception as exc:
            try:
                self._write_sse("error", {"message": "An error occurred during the turn."})
            except _ClientDisconnected:
                pass
        finally:
            lock.release()

    def _write_sse(self, event_type: str, data: dict[str, Any]) -> None:
        """Write one SSE frame."""
        payload = json.dumps({"type": event_type, **data}, ensure_ascii=False)
        frame = f"event: {event_type}\ndata: {payload}\n\n"
        try:
            self.wfile.write(frame.encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            # Browser closed the connection — stop writing
            raise _ClientDisconnected()

    # ------------------------------------------------------------------
    # Static file serving
    # ------------------------------------------------------------------

    def _serve_html(self) -> None:
        import importlib.resources
        try:
            html = (
                importlib.resources.files("palimpsest.templates")
                .joinpath("index.html")
                .read_text(encoding="utf-8")
            )
        except Exception:
            html = "<!doctype html><h1>Palimpsest</h1><p>index.html not found.</p>"
        self._text(html, "text/html; charset=utf-8")

    def _serve_vendor(self, filename: str) -> None:
        import importlib.resources
        # Sanitize filename — no path traversal
        safe = Path(filename).name
        try:
            content = (
                importlib.resources.files("palimpsest.templates")
                .joinpath("vendor")
                .joinpath(safe)
                .read_bytes()
            )
        except Exception:
            return self._error(404, f"Vendor file {safe!r} not found")

        ct = "application/javascript"
        if safe.endswith(".css"):
            ct = "text/css"
        elif safe.endswith(".svg"):
            ct = "image/svg+xml"
        self._bytes(content, ct)

    def _serve_capture(self, case_dir: Path, filename: str) -> None:
        safe = Path(filename).name
        capture_file = case_dir / "captures" / safe
        if not capture_file.is_file():
            return self._error(404, "Capture not found")
        self._serve_file(capture_file, "text/html; charset=utf-8")

    def _serve_file(self, path: Path, content_type: str) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            return self._error(500, "Cannot read file")
        self._bytes(data, content_type)

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def _json(self, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, text: str, content_type: str) -> None:
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, data: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ------------------------------------------------------------------
# Agent management
# ------------------------------------------------------------------

_agents: dict[str, Agent] = {}
_locks: dict[str, threading.Lock] = {}


def _get_agent(slug: str) -> Agent:
    """Get or create a cached Agent for *slug*."""
    if slug not in _agents:
        _agents[slug] = Agent(slug)
    return _agents[slug]


def _get_case_lock(slug: str) -> threading.Lock:
    """Get or create a per-case threading lock."""
    if slug not in _locks:
        _locks[slug] = threading.Lock()
    return _locks[slug]


# ------------------------------------------------------------------
# run_turn_sync — synchronous wrapper for the async agent turn
# ------------------------------------------------------------------

class _ClientDisconnected(Exception):
    """Raised when the SSE client disconnects."""


# Patch Agent to add a synchronous turn runner for the web server
def _run_turn_sync_patch(self: Agent, user_message: str,
                         on_event: Any = None) -> str:
    """Synchronous wrapper around the async turn. Used by the web server.

    Closes the MCP client after each turn so the next request — which
    runs in a fresh ``asyncio.run()`` event loop — starts clean.
    """
    import asyncio

    final_text: str = ""

    async def _do() -> None:
        nonlocal final_text
        try:
            await self._run_turn(user_message, on_event=on_event)
            for msg in reversed(self.messages):
                if msg.get("role") == "assistant" and msg.get("content"):
                    final_text = msg["content"]
                    return
        finally:
            await self.close()

    try:
        asyncio.run(_do())
    except RuntimeError:
        # Event loop already running — use existing loop (shouldn't happen
        # with ThreadingHTTPServer, but handle gracefully)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_do())

    return final_text


Agent.run_turn_sync = _run_turn_sync_patch  # type: ignore[attr-defined]


# ------------------------------------------------------------------
# Server entry point
# ------------------------------------------------------------------

def serve(port: int = DEFAULT_PORT, host: str = DEFAULT_HOST,
          no_browser: bool = False) -> None:
    """Start the HTTP server and optionally open a browser tab."""
    server = ThreadingHTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}"
    shutdown = threading.Event()

    def _on_signal(signum: int, frame: Any) -> None:
        shutdown.set()

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    print(f"╭─ Palimpsest")
    print(f"├─ {url}")
    print(f"╰─ Press Ctrl+C to stop")

    if not no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    # Run serve_forever in a daemon thread, wait for shutdown signal
    server_thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True)
    server_thread.start()

    try:
        shutdown.wait()
    except KeyboardInterrupt:
        pass

    print("\nShutting down...")
    # Close all cached agent MCP clients
    for agent in _agents.values():
        try:
            asyncio.run(agent.close())
        except Exception:
            pass
    server.shutdown()
    server_thread.join(timeout=2)
