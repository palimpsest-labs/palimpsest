# Contributing to Palimpsest

Thanks for your interest. This is a small, focused project — contributions that align with the design principles are welcome.

## Design Principles (non-negotiable)

These are the constraints that shape every decision. PRs that violate them won't be merged.

1. **Local-first** — no cloud dependencies for core functionality
2. **Source provenance** — every finding traceable to origin
3. **Never delete** — append-only data, immutable audit trail
4. **Offline-capable** — core functions work without internet
5. **Chain of custody** — evidence must be legally defensible
6. **Simple tools** — prefer bash scripts over frameworks, stdlib over dependencies

## Development Setup

```bash
git clone https://github.com/palimpsest-labs/palimpsest
cd palimpsest
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
pytest --cov=palimpsest
```

## Project Structure

```
palimpsest/
├── skills/
│   └── investigative-journalist/
│       └── SKILL.md              # The investigative methodology (the brain)
├── src/palimpsest/
│   ├── __init__.py
│   ├── __main__.py               # CLI entry point
│   ├── capture.py                # Evidence capture system
│   └── templates/
│       ├── dossier.md            # Investigation report template
│       ├── timeline.md           # Timeline template
│       └── network-map.md        # Network/relationship map template
├── research-tools.sh             # Wayback, Companies House, WHOIS, RDAP
├── tests/
├── ROADMAP.md
└── README.md
```

## What to Contribute

The roadmap (ROADMAP.md) tracks planned work. Good first contributions:

- Adding tests for `capture.py` or `research-tools.sh`
- Improving the skill's methodology (SKILL.md) — especially legal awareness for non-UK jurisdictions
- Adding new platform APIs to `research-tools.sh` (e.g., certificate transparency logs, OpenCorporates)
- Synthetic demo dataset for testing and onboarding
- Documentation improvements

## What Not to Contribute

- Cloud dependencies or services
- Real-time collaboration features (Phase 6, not now)
- LinkedIn scraping (legal risk — see ROADMAP.md design discussion)
- Frameworks that add heavy dependency trees
- PDF generation infrastructure (pandoc is a one-liner)

## Code Style

- Python: follow PEP 8. Type hints encouraged but not required.
- Bash: shellcheck-clean. Use `set -euo pipefail`.
- Skill docs: plain markdown, keep it practical. Write for journalists, not engineers.

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Companies House API lookup
fix: handle RDAP fallback when whois not installed
docs: add GDPR considerations to skill
test: add capture.py unit tests
```

## License

MIT. By contributing, you agree to license your work under the same terms.
