"""Web page snapshot capture with SHA-256 hashing and chain-of-custody manifest.

Usage:
    python -m palimpsest.capture <url> [--output-dir captures]

The module is also importable:
    from palimpsest.capture import capture_url
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

USER_AGENT = "Palimpsest/0.1 (+https://github.com/jmars/palimpsest)"
FETCH_TIMEOUT = 30
WAYBACK_TIMEOUT = 5


def fetch_url(url: str, timeout: int = FETCH_TIMEOUT) -> tuple[bytes, int, str | None]:
    """Fetch a URL and return (body, status_code, content_type).

    Raises urllib.error.URLError or ValueError on failure.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
            content_type = resp.headers.get("Content-Type")
            return body, status, content_type
    except urllib.error.HTTPError as exc:
        raise ValueError(
            f"HTTP {exc.code} fetching {url}: {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ValueError(
            f"URL error fetching {url}: {exc.reason}"
        ) from exc


def compute_sha256(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def check_wayback(url: str, timeout: int = WAYBACK_TIMEOUT) -> str | None:
    """Check the Wayback Machine for an existing archive of *url*.

    Returns the most recent snapshot URL, or *None* if no archive is found
    or the lookup fails.
    """
    cdx_url = (
        "https://web.archive.org/cdx/search/cdx"
        f"?url={urllib.parse.quote(url)}"
        "&output=json&limit=1&fl=timestamp,original&sort=timestamp&from=0"
    )
    req = urllib.request.Request(cdx_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if not data or len(data) < 2:
        return None

    timestamp = data[1][0]  # e.g. "20250321120000"
    original = data[1][1]
    wayback_url = f"https://web.archive.org/web/{timestamp}/{original}"
    return wayback_url


def save_capture(body: bytes, sha256_digest: str, output_dir: str) -> str:
    """Save *body* to *output_dir*/*<sha256_digest>*.html.

    Returns the absolute path to the saved file.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{sha256_digest}.html")
    with open(filepath, "wb") as f:
        f.write(body)
    return os.path.abspath(filepath)


def append_manifest(
    output_dir: str,
    entry: dict[str, Any],
) -> None:
    """Append a JSON line to the manifest file."""
    manifest_path = os.path.join(output_dir, "manifest.jsonl")
    with open(manifest_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def capture_url(
    url: str,
    output_dir: str = "captures",
) -> dict[str, Any]:
    """Fetch a URL, save the response body, record a manifest entry.

    Returns the manifest entry dict on success.

    Raises ValueError (with a human-readable message) on HTTP or network
    errors.  The caller is responsible for catching the exception.
    """
    # 1. Fetch
    body, status_code, content_type = fetch_url(url)

    # 2. Hash
    sha256_digest = compute_sha256(body)

    # 3. Save
    capture_path = save_capture(body, sha256_digest, output_dir)

    # 4. Wayback
    wayback_url = check_wayback(url)

    # 5. Manifest entry
    timestamp = datetime.now(timezone.utc).isoformat()
    entry: dict[str, Any] = {
        "url": url,
        "timestamp": timestamp,
        "sha256": sha256_digest,
        "status_code": status_code,
        "wayback_url": wayback_url,
        "content_type": content_type,
    }
    append_manifest(output_dir, entry)

    return entry


def print_summary(entry: dict[str, Any], capture_path: str) -> None:
    """Print a markdown summary of the capture to stdout."""
    wayback = entry["wayback_url"] if entry["wayback_url"] else "none"
    print(f"**URL:** {entry['url']}")
    print(f"**Status:** {entry['status_code']}")
    print(f"**SHA-256:** `{entry['sha256']}`")
    print(f"**Content-Type:** {entry['content_type']}")
    print(f"**Wayback:** {wayback}")
    print(f"**Capture:** `{capture_path}`")
    print("**Manifest:** entry added")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture a web page snapshot with chain-of-custody metadata.",
    )
    parser.add_argument("url", help="URL to capture")
    parser.add_argument(
        "--output-dir",
        default="captures",
        help="Output directory for captured files and manifest (default: captures)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        entry = capture_url(args.url, output_dir=args.output_dir)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    capture_path = os.path.abspath(
        os.path.join(args.output_dir, f"{entry['sha256']}.html")
    )
    print_summary(entry, capture_path)


if __name__ == "__main__":
    main()
