from __future__ import annotations

from pathlib import Path

import pytest


def test_vendor_schema_root_is_used_by_default() -> None:
    # This test enforces Phase 3 objective:
    # The canonical schema root should be vendor-backed (vendor/swe-schemas),
    # not an ad-hoc local copy.
    import swe_bootstrap
    swe_bootstrap.apply()

    import swe_schemas

    # resolve_schema_root() must exist and point to a real directory.
    root = getattr(swe_schemas, "resolve_schema_root", None)
    assert callable(root), "swe_schemas.resolve_schema_root() is required"

    p = root(None)
    assert isinstance(p, Path)
    assert p.exists() and p.is_dir(), f"schema_root must exist: {p}"

    # Must be vendor-backed (path contains vendor/swe-schemas)
    norm = str(p).replace("\\", "/").lower()
    assert "/vendor/" in norm and "swe-schemas" in norm, f"schema_root not vendor-backed: {p}"
