from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.validation.schema_validation import validate_payload

def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(50):
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            return cur
        cur = cur.parent
    return start.resolve()

def _find_any_fixture_with_contract(fixtures_root: Path) -> Path | None:
    for p in fixtures_root.rglob("*.json"):
        s = str(p).replace("\\", "/").lower()
        if "/.git/" in s:
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("contract"), str) and obj["contract"].strip():
            return p
    return None

def test_validate_fixture_via_vendor_schemas() -> None:
    repo = _find_repo_root(Path(__file__))
    fixtures = repo / "vendor" / "swe-fixtures"
    if not fixtures.exists():
        pytest.skip("vendor/swe-fixtures submodule not present")
    fx = _find_any_fixture_with_contract(fixtures)
    if fx is None:
        pytest.skip("no JSON fixture with a 'contract' field found")
    payload = json.loads(fx.read_text(encoding="utf-8"))
    validate_payload(payload)
