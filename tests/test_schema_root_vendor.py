from __future__ import annotations

from pathlib import Path

from app.schema_locator import default_schema_root, resolve_schema_root

def test_default_schema_root_is_vendor_submodule() -> None:
    root = default_schema_root()
    assert root.name == "swe-schemas"
    assert (root / ".git").exists() or root.exists(), "vendor/swe-schemas must exist (submodule pinned)"
    # Must be under repo/vendor/swe-schemas
    repo = Path(__file__).resolve()
    for _ in range(50):
        if (repo / "pyproject.toml").exists() or (repo / ".git").exists():
            break
        repo = repo.parent
    assert (repo / "vendor" / "swe-schemas").resolve() == root

def test_resolve_schema_root_prefers_env_then_default(monkeypatch) -> None:
    monkeypatch.delenv("SWE_SCHEMA_ROOT", raising=False)
    monkeypatch.delenv("SWE_SCHEMA_DIR", raising=False)
    assert resolve_schema_root(None) == default_schema_root()

    monkeypatch.setenv("SWE_SCHEMA_ROOT", str(default_schema_root()))
    assert resolve_schema_root(None) == default_schema_root()
