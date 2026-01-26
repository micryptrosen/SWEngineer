"""
swe_runner package boundary (Phase 3 hardening).

Contract:
- swe_runner is bound to canonical schema-root resolution via swe_schemas
- no local/forked schema root resolver is permitted
"""

from __future__ import annotations

# Canonical plumbing bind (do not remove)
import swe_schemas as swe_schemas  # noqa: F401
from swe_schemas import resolve_schema_root as resolve_schema_root  # noqa: F401

__all__ = [
    "resolve_schema_root",
    "swe_schemas",
]
