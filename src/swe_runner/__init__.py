from __future__ import annotations

"""
swe_runner package

Contract:
- Must NOT cache schema root or bind resolver at import time.
- Must resolve via canonical swe_schemas at call-time.
"""

from pathlib import Path
import swe_schemas


def resolve_schema_root() -> Path:
    """
    Call-time binding to the canonical resolver.

    IMPORTANT:
    Do not alias/import the function directly:
      from swe_schemas import resolve_schema_root
    because monkeypatching swe_schemas.resolve_schema_root must be observable here.
    """
    return swe_schemas.resolve_schema_root()

