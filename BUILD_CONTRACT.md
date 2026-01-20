# Build Contract (Locked)

Repo root: C:\Dev\CCP\SWEngineer

## Canonical Tooling Config
- pyproject.toml is the single source of truth for tooling configuration.

## Dependencies
- Runtime: requirements.txt
- Dev/tooling: requirements-dev.txt

## Gates
- Authoritative runner: tools/gates.py
- Local: Run-Gates.ps1 (mints .gates/LAST_GREEN.txt)
- CI: runs python tools/gates.py --mode ci

## Commit Policy (Non-negotiable)
- No commits on RED gates.
- Commit Firewall enforced by pre-commit hook requiring .gates/LAST_GREEN.txt.

## Line Endings
- Controlled by .gitattributes and .editorconfig.
