"""
swe_runner package boundary (Phase 3 hardening).

Contract:
- swe_runner is bound to canonical schema-root resolution via swe_schemas
- no local/forked schema root resolver is permitted
"""

from __future__ import annotations
import swe_schemas as swe_schemas

# Canonical plumbing bind (do not remove)
import swe_schemas as swe_schemas  # noqa: F401


def resolve_schema_root() -> str:
    """Call-time schema root resolution (Phase 3 / Step 3M)."""
    return swe_schemas.resolve_schema_root()


__all__ = [
    "resolve_schema_root",
    "swe_schemas",
]
