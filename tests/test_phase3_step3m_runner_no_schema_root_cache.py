from __future__ import annotations

from pathlib import Path
import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_runner_does_not_cache_schema_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Phase 3 / Step 3M contract:

    swe_runner must not cache schema root in a module constant at import time.
    It must resolve via canonical swe_schemas at call-time.

    This protects against stale roots when vendor submodule path changes.
    """
    import swe_bootstrap
    swe_bootstrap.apply()

    import swe_schemas
    import swe_runner

    # Contract part A: no obvious schema-root cache constants
    d = getattr(swe_runner, "__dict__", {})
    forbidden = [k for k in d.keys() if k.upper() in ("SCHEMA_ROOT", "SCHEMAS_ROOT", "SCHEMA_DIR", "SCHEMA_PATH")]
    assert not forbidden, f"swe_runner appears to cache schema root: {forbidden}"

    # Contract part B: call-time binding observed via monkeypatch
    sentinel = _repo_root() / "vendor" / "swe-schemas__SENTINEL__"
    monkeypatch.setattr(swe_schemas, "resolve_schema_root", lambda: sentinel)

    # Must reflect patched resolver at call-time.
    got = Path(swe_runner.resolve_schema_root()).resolve()
    assert got == sentinel.resolve(), f"runner did not resolve at call-time: got={got} expected={sentinel}"
