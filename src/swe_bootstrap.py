from __future__ import annotations

"""
swe_bootstrap
Phase 3 contract:
- Import-safe (no import-time side effects beyond defining functions)
- apply() must make repo-local imports deterministic, including:
  - src/*
  - app/* (GUI + validation package tree)
  - vendor/swe-schemas (canonical schemas)
"""

from pathlib import Path
import sys


def _ins(p: Path) -> None:
    s = str(p)
    if p.exists() and s not in sys.path:
        sys.path.insert(0, s)


def _find_repo_root(start: Path) -> Path:
    """
    Walk upward to find the repository root using stable markers.
    """
    cur = start.resolve()
    for _ in range(12):
        if (cur / ".git").exists():
            return cur
        if (cur / "requirements-dev.txt").exists():
            return cur
        if (cur / "pyproject.toml").exists():
            return cur
        if (cur / "src").exists() and (cur / "vendor").exists():
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    # Fallback: assume typical layout (repo/src/...)
    return start.resolve().parents[1]


def apply() -> None:
    """
    Deterministically inject required paths for SWEngineer runtime imports.

    Under isolated (-I) mode, tests inject ONLY repo/src before importing swe_bootstrap.
    Therefore apply() must expand sys.path to include:
      - repo root
      - repo/src
      - repo/app
      - repo/vendor/swe-schemas
    """
    here = Path(__file__).resolve()
    repo = _find_repo_root(here)

    _ins(repo)
    _ins(repo / "src")
    _ins(repo / "app")
    _ins(repo / "vendor" / "swe-schemas")
