from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

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
    return here.parents[2]

def resolve_schema_root(schema_root: Optional[Union[str, Path]] = None) -> Path:
    """
    Resolve the canonical schema root directory.

    Precedence:
      1) explicit argument (if provided)
      2) env override (first match in _ENV_KEYS)
      3) default: <repo>/vendor/swe-schemas (repo derived from this module path)

    Contract:
      - Returns pathlib.Path (not str).
      - MUST NOT fall back to any path outside the current repo when no override is provided.
      - MUST be stable under clean clone + python -I with src injected.
    """
    if schema_root is not None:
        return Path(schema_root).resolve()

    for k in _ENV_KEYS:
        v = os.environ.get(k)
        if v and v.strip():
            return Path(v).resolve()

    repo = _repo_root_from_module()
    return (repo / "vendor" / "swe-schemas").resolve()

__all__ = ["resolve_schema_root"]
