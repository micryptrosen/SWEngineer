from __future__ import annotations

import sys
from pathlib import Path

def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(15):
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    return start.resolve()

def apply(repo_root: str | None = None) -> None:
    """
    Deterministic bootstrap for SWEngineer.

    Purpose:
      - Ensure vendored swe-schemas import root (`schemas`) is discoverable
      - Ensure local src/ is discoverable
      - Provide stable environment for both swe-runner and GUI/planner validation

    Contract:
      - Must be safe to call multiple times
      - Must NOT write files
      - Must only mutate sys.path in a minimal, deterministic way
    """
    root = Path(repo_root) if repo_root else _find_repo_root(Path.cwd())

    vendor_swe_schemas = root / "vendor" / "swe-schemas"
    src = root / "src"

    # Priority order: vendor first, then src
    inserts = []
    if vendor_swe_schemas.exists():
        inserts.append(str(vendor_swe_schemas))
    if src.exists():
        inserts.append(str(src))

    for p in reversed(inserts):
        if p not in sys.path:
            sys.path.insert(0, p)
