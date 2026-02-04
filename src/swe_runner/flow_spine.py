from __future__ import annotations

"""
flow_spine

Phase2C(A) contract:
- Do not define local resolve_schema_root.
- Always bind schema root via swe_schemas.resolve_schema_root().
"""

from pathlib import Path

from swe_schemas import resolve_schema_root


def schema_root() -> Path:
    """
    Canonical schema root for runner flows.
    """
    return resolve_schema_root()

