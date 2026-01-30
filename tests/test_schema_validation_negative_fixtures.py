from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _collect_negative_run_handoff_fixtures() -> List[Path]:
    root = _repo_root()
    base = root / "vendor" / "swe-fixtures" / "run_handoff" / "bad"
    if not base.exists():
        # If upstream removes bad fixtures, this test should not fail the suite.
        # It becomes a no-op, but stays as a contract placeholder.
        return []
    fixtures = sorted([p for p in base.rglob("*.json") if p.is_file()])
    return fixtures


def _load_json(p: Path) -> dict:
    raw = p.read_bytes()
    txt = raw.decode("utf-8")
    return json.loads(txt)


@pytest.mark.parametrize("fixture_path", _collect_negative_run_handoff_fixtures(), ids=lambda p: str(p))
def test_negative_run_handoff_fixtures_are_rejected(fixture_path: Path) -> None:
    """
    Negative-fixture contract: fixtures under run_handoff/bad/** must be rejected by validate_payload().
    This ensures negative fixtures remain negative and prevents accidental 'green' acceptance.
    """
    payload = _load_json(fixture_path)

    from app.validation.schema_validation import validate_payload

    with pytest.raises(Exception):
        validate_payload(payload)