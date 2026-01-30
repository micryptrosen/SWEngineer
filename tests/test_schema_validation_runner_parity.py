from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

import pytest

# Contract: parity tests MUST only use positive fixtures.
# Negative fixtures (e.g., vendor/swe-fixtures/**/bad/**) are validated by dedicated negative tests (Step 5IK),
# and must never be auto-discovered by parity selection.


def _repo_root() -> Path:
    # tests/ is at repo_root/tests/
    return Path(__file__).resolve().parents[1]


def _collect_positive_run_handoff_fixtures() -> List[Path]:
    root = _repo_root()
    base = root / "vendor" / "swe-fixtures" / "run_handoff" / "good"
    if not base.exists():
        raise AssertionError(f"Positive fixtures directory not found: {base}")

    fixtures = sorted([p for p in base.rglob("*.json") if p.is_file()])

    # Guardrails: never pick negative fixtures, even if directory structure drifts.
    bad_hits = [p for p in fixtures if "bad" in p.parts]
    if bad_hits:
        joined = "\n".join(str(p) for p in bad_hits[:25])
        raise AssertionError(
            "Parity fixture discovery violated policy: found fixture(s) under a 'bad' path.\n"
            f"First hits:\n{joined}"
        )

    if not fixtures:
        raise AssertionError(f"No positive fixtures discovered under: {base}")

    return fixtures


def _load_json(p: Path) -> dict:
    # Read as bytes then decode to avoid newline translation differences.
    raw = p.read_bytes()
    txt = raw.decode("utf-8")
    return json.loads(txt)


@pytest.mark.parametrize("fixture_path", _collect_positive_run_handoff_fixtures(), ids=lambda p: str(p))
def test_runner_parity_positive_fixtures_validate(fixture_path: Path) -> None:
    """
    Parity contract: every positive run_handoff fixture must validate under vendor schemas.
    This test intentionally does NOT attempt to validate any negative fixtures.
    """
    payload = _load_json(fixture_path)

    # Validate using the canonical validator entrypoint.
    # NOTE: This relies on SWEngineer’s existing validate_payload API raising on failure.
    from app.validation.schema_validation import validate_payload

    validate_payload(payload)


def test_runner_parity_fixture_policy_is_positive_only() -> None:
    """
    Extra guard: ensure our discovery root is explicitly 'good' and we never scan the parent tree.
    """
    root = _repo_root()
    good_dir = root / "vendor" / "swe-fixtures" / "run_handoff" / "good"
    assert good_dir.exists(), f"Expected good fixtures directory: {good_dir}"

    # Sanity: if bad exists, it must not be selected by parity discovery.
    bad_dir = root / "vendor" / "swe-fixtures" / "run_handoff" / "bad"
    if bad_dir.exists():
        selected = set(_collect_positive_run_handoff_fixtures())
        leaked = [p for p in selected if "bad" in p.parts]
        assert not leaked, "Parity discovery leaked a bad fixture unexpectedly."