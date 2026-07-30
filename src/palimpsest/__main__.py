"""CLI entry point for Palimpsest."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        _usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd in ("-h", "--help", "help"):
        _usage()
    elif cmd in ("-v", "--version", "version"):
        from . import __version__
        print(f"palimpsest v{__version__}")
    elif cmd == "new":
        _cmd_new(sys.argv[2:])
    elif cmd == "list":
        _cmd_list()
    elif cmd == "agent":
        _cmd_agent(sys.argv[2:])
    elif cmd == "repl":
        _cmd_repl(sys.argv[2:])
    elif cmd == "dossier":
        _cmd_dossier(sys.argv[2:])
    elif cmd == "wayback":
        _cmd_research("wayback", sys.argv[2:])
    elif cmd == "company":
        _cmd_research("companies-house", sys.argv[2:])
    elif cmd == "whois":
        _cmd_research("whois", sys.argv[2:])
    elif cmd == "rdap":
        _cmd_research("rdap", sys.argv[2:])
    elif cmd == "capture":
        _cmd_capture(sys.argv[2:])
    elif cmd == "serve":
        _cmd_serve(sys.argv[2:])
    else:
        print(f"Unknown command: {cmd}")
        _usage()
        sys.exit(1)


def _usage() -> None:
    print("""Palimpsest — investigative journalism research engine

Usage:
  palimpsest new <slug> [--title "Investigation Title"]
  palimpsest list
  palimpsest agent <slug>              # Interactive REPL (default)
  palimpsest agent <slug> --message "..."  # One-shot mode
  palimpsest repl <slug>               # Explicit REPL (same as agent without --message)
  palimpsest dossier <slug>
  palimpsest wayback <url> [--from YEAR] [--to YEAR]
  palimpsest company <number>
  palimpsest whois <domain>
  palimpsest rdap <domain>
  palimpsest capture <url> --case <slug>
  palimpsest serve [--port PORT] [--no-browser]

Environment:
  PALIMPSEST_LLM_URL     LLM endpoint (default: http://127.0.0.1:8000/v1)
  PALIMPSEST_MODEL       Model name (default: deepseek-v4-flash)
  PALIMPSEST_API_KEY     API key (default: dsv4-local)
  COMPANIES_HOUSE_API_KEY  UK Companies House API key

Example:
  palimpsest new telecom-nexus --title "Telecom Industry Nexus"
  palimpsest agent telecom-nexus
  palimpsest agent telecom-nexus --message "Investigate the connection between these companies."
""")


def _cmd_new(args: list[str]) -> None:
    slug = None
    title = ""
    i = 0
    while i < len(args):
        if args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif not slug and not args[i].startswith("-"):
            slug = args[i]
            i += 1
        else:
            i += 1

    if not slug:
        print("Error: slug required. Usage: palimpsest new <slug> [--title ...]")
        sys.exit(1)

    from .case import create_case
    try:
        case_dir = create_case(slug, title)
        print(f"Created case: {case_dir}")
        print(f"  memory:   {case_dir / 'memory.jsonl'}")
        print(f"  captures: {case_dir / 'captures'}/")
        print(f"  state:    {case_dir / 'state.json'}")
        print(f"\nNext: palimpsest agent {slug} --message 'What to investigate'")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def _cmd_list() -> None:
    from .case import list_cases
    cases = list_cases()
    if not cases:
        print("No cases found.")
        return
    print(f"{'SLUG':<30} {'PHASE':<15} {'TITLE'}")
    print("-" * 80)
    for c in cases:
        print(f"{c['slug']:<30} {c['phase']:<15} {c['title']}")


def _cmd_agent(args: list[str]) -> None:
    slug = None
    message = None
    i = 0
    while i < len(args):
        if args[i] in ("-m", "--message") and i + 1 < len(args):
            message = args[i + 1]
            i += 2
        elif not slug and not args[i].startswith("-"):
            slug = args[i]
            i += 1
        else:
            i += 1

    if not slug:
        print("Error: slug required. Usage: palimpsest agent <slug> [--message ...]")
        sys.exit(1)

    from .agent import Agent
    agent = Agent(slug)
    try:
        if message:
            # One-shot mode
            asyncio.run(agent.run(message))
        else:
            # Interactive REPL mode
            asyncio.run(agent.repl())
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted. State saved.")


def _cmd_repl(args: list[str]) -> None:
    """Explicit REPL command — same as 'agent' without --message."""
    if not args:
        print("Error: slug required. Usage: palimpsest repl <slug>")
        sys.exit(1)
    slug = args[0]
    from .agent import Agent
    agent = Agent(slug)
    try:
        asyncio.run(agent.repl())
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted. State saved.")


def _cmd_dossier(args: list[str]) -> None:
    if not args:
        print("Error: slug required. Usage: palimpsest dossier <slug>")
        sys.exit(1)
    slug = args[0]

    from .case import get_case_dir
    from .gates import check_dossier_ready
    case_dir = get_case_dir(slug)
    issues = check_dossier_ready(case_dir)
    if issues:
        print("Dossier not ready:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)

    print(f"Dossier generation for '{slug}' — coming in v0.2.0")


def _cmd_research(tool: str, args: list[str]) -> None:
    import subprocess
    tools_sh = Path(__file__).resolve().parent.parent.parent / "research-tools.sh"
    cmd = [str(tools_sh), tool] + [a for a in args if a != "--json"] + ["--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print(result.stdout)


def _cmd_capture(args: list[str]) -> None:
    url = None
    case_slug = None
    i = 0
    while i < len(args):
        if args[i] in ("-c", "--case") and i + 1 < len(args):
            case_slug = args[i + 1]
            i += 2
        elif not url and not args[i].startswith("-"):
            url = args[i]
            i += 1
        else:
            i += 1

    if not url or not case_slug:
        print("Error: url and --case required. Usage: palimpsest capture <url> --case <slug>")
        sys.exit(1)

    from .case import get_case_dir
    from .capture import capture_url
    case_dir = get_case_dir(case_slug)
    captures_dir = str(case_dir / "captures")
    try:
        entry = capture_url(url, captures_dir)
        print(f"Captured: {entry['url']}")
        print(f"  Status:   {entry['status_code']}")
        print(f"  SHA-256:  {entry['sha256']}")
        print(f"  Wayback:  {entry.get('wayback_url') or 'none'}")
        print(f"  Manifest: {captures_dir}/manifest.jsonl")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_serve(args: list[str]) -> None:
    port = None
    no_browser = False
    i = 0
    while i < len(args):
        if args[i] in ("-p", "--port") and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                print(f"Invalid port: {args[i + 1]}")
                sys.exit(1)
            i += 2
        elif args[i] == "--no-browser":
            no_browser = True
            i += 1
        else:
            i += 1

    from .server import serve, DEFAULT_PORT
    kwargs = {"no_browser": no_browser}
    if port is not None:
        kwargs["port"] = port
    serve(**kwargs)


if __name__ == "__main__":
    main()
