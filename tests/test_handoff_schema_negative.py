from __future__ import annotations

from pathlib import Path
import pytest

from app.gui.planner import GuiStore, make_run_plan, persist_run_plan, make_approval, persist_approval, persist_handoff_from_plan
from app.validation.schema_validation import SchemaValidationError


def test_handoff_missing_sha_is_rejected(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)

    # Create a valid handoff record first (should pass)
    rec = persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")

    # Now mutate payload to remove sha and confirm schema rejects it
    import json
    obj = json.loads(rec.body)
    obj.pop("payload_sha256", None)

    from app.validation.schema_validation import validate_payload
    with pytest.raises(SchemaValidationError):
        validate_payload(obj)


def test_handoff_bad_sha_is_rejected(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)

    rec = persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")

    import json
    obj = json.loads(rec.body)
    obj["payload_sha256"] = "abc123"  # invalid length/pattern

    from app.validation.schema_validation import validate_payload
    with pytest.raises(SchemaValidationError):
        validate_payload(obj)
