from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# NOTE:
# Clean-clone determinism requirement:
# - Default schema root MUST be derived from THIS module location (src-layout),
#   never from any external/previous checkout path.
# - Env override is allowed (runner contract), but bootstrap may sanitize it.

_ENV_KEYS = (
    "SWE_SCHEMA_ROOT",
    "SWE_SCHEMAS_ROOT",
    "SWENGINEER_SCHEMA_ROOT",
)

def _repo_root_from_module() -> Path:
    # <repo>/src/swe_schemas/__init__.py -> parents[2] == <repo>
    here = Path(__file__).resolve()
    repo = here.parents[2]
    return repo

def resolve_schema_root(schema_root: Optional[str] = None) -> str:
    """
    Resolve the canonical schema root directory.

    Precedence:
      1) explicit argument (if provided)
      2) env override (first match in _ENV_KEYS)
      3) default: <repo>/vendor/swe-schemas (repo derived from this module path)

    Contract:
      - MUST NOT fall back to any path outside the current repo when no override is provided.
      - MUST be stable under clean clone + python -I with src injected.
    """
    if schema_root:
        return str(Path(schema_root).resolve())

    for k in _ENV_KEYS:
        v = os.environ.get(k)
        if v and v.strip():
            return str(Path(v).resolve())

    repo = _repo_root_from_module()
    vendor = (repo / "vendor" / "swe-schemas").resolve()
    return str(vendor)

__all__ = ["resolve_schema_root"]
