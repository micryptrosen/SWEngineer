from __future__ import annotations

from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_validator_default_schema_root_is_vendor_backed(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Phase 3 / Step 3H invariant:
    - Validator must resolve schemas from swe_schemas.resolve_schema_root() by default.
    - That resolver must point to vendor/swe-schemas.
    - Validator must NOT silently fall back to any other directory when schema_root is None.
    """
    import swe_bootstrap
    swe_bootstrap.apply()

    import swe_schemas
    from app.validation.schema_validation import resolve_schema_root as validator_resolve_root

    repo = _repo_root()
    expected = (repo / "vendor" / "swe-schemas").resolve()

    root1 = swe_schemas.resolve_schema_root()
    assert Path(root1).resolve() == expected
    assert expected.exists()

    root2 = validator_resolve_root(None)
    assert Path(root2).resolve() == expected

    missing = repo / "vendor" / "swe-schemas__MISSING__"
    monkeypatch.setattr(swe_schemas, "resolve_schema_root", lambda: missing)

    from app.validation.schema_validation import SchemaValidationError, resolve_schema_root as validator_resolve_root2

    with pytest.raises(SchemaValidationError):
        validator_resolve_root2(None)
