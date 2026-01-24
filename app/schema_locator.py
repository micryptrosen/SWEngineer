from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(50):
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            return cur
        cur = cur.parent
    return start.resolve()


def default_schema_root() -> Path:
    """
    Canonical default schema root (pinned by submodule commit):
      <repo>/vendor/swe-schemas
    """
    repo = _find_repo_root(Path(__file__).resolve())
    return (repo / "vendor" / "swe-schemas").resolve()


def resolve_schema_root(schema_root: Optional[PathLike] = None) -> Path:
    """
    Resolution order:
      1) explicit arg (schema_root)
      2) env SWE_SCHEMA_ROOT (or SWE_SCHEMA_DIR)
      3) canonical default vendor path
    """
    if schema_root is None:
        env = os.environ.get("SWE_SCHEMA_ROOT") or os.environ.get("SWE_SCHEMA_DIR")
        if env:
            schema_root = env

    root = Path(schema_root) if schema_root is not None else default_schema_root()
    return root.resolve()
