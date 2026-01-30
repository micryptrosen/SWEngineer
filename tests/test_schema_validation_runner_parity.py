from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

from app.validation.schema_validation import validate_payload


def _find_repo_root(p: Path) -> Path:
    cur = p.resolve()
    for _ in range(0, 20):
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p.resolve().parent


def _has_contract_field(p: Path) -> bool:
    try:
        txt = p.read_text(encoding="utf-8")
    except Exception:
        return False
    return '"contract"' in txt


def _is_bad_fixture_path(p: Path) -> bool:
    parts = [x.lower() for x in p.parts]
    return "bad" in parts


def _find_any_fixture_with_contract(fixtures_root: Path) -> Optional[Path]:
    # Prefer "good" fixtures and never select known "bad" fixtures (which intentionally fail sha checks).
    good = []
    ok = []
    for p in fixtures_root.rglob("*.json"):
        if not _has_contract_field(p):
            continue
        if _is_bad_fixture_path(p):
            continue
        parts = [x.lower() for x in p.parts]
        if "good" in parts:
            good.append(p)
        else:
            ok.append(p)
    if good:
        return sorted(good)[0]
    if ok:
        return sorted(ok)[0]
    return None


def test_validate_fixture_via_vendor_schemas() -> None:
    repo = _find_repo_root(Path(__file__))
    fixtures = repo / "vendor" / "swe-fixtures"
    if not fixtures.exists():
        pytest.skip("vendor/swe-fixtures submodule not present")

    fx = _find_any_fixture_with_contract(fixtures)
    if fx is None:
        pytest.skip("no non-bad JSON fixture with a 'contract' field found")

    payload = json.loads(fx.read_text(encoding="utf-8"))
    validate_payload(payload)
