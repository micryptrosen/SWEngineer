from __future__ import annotations

import os

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
def _purge_shadow_schema_env(repo_root):
    """
    Clean-clone determinism:
    If a globally-set schema root env var points OUTSIDE this repo, ignore it.
    This prevents shadow binding to a different working copy (e.g., C:\\Dev\\CCP\\SWEngineer).
    """
    try:
        from pathlib import Path
    except Exception:
        return

    rr = Path(repo_root).resolve()
    keys = [
        "SWE_SCHEMA_ROOT",
        "SWE_SCHEMAS_ROOT",
        "SCHEMA_ROOT",
        "SWENGINEER_SCHEMA_ROOT",
    ]

    for k in keys:
        v = os.environ.get(k)
        if not v:
            continue
        try:
            cand = Path(v).expanduser().resolve()
        except Exception:
            # If it can't resolve, drop it (non-deterministic)
            os.environ.pop(k, None)
            continue

        # Allow only schema roots that are inside THIS repo
        try:
            inside = cand.is_relative_to(rr)
        except Exception:
            # Py<3.9 fallback (shouldn't happen on 3.12, but keep deterministic)
            inside = str(cand).lower().startswith(str(rr).lower())

        if not inside:
            os.environ.pop(k, None)

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

