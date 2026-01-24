from __future__ import annotations

from pathlib import Path
import json

from app.gui.planner import GuiStore, make_run_plan, persist_run_plan, make_approval, persist_approval, persist_handoff_from_plan
from app.validation.schema_validation import validate_payload


def test_gui_handoff_validates_under_vendor_schemas(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)

    rec = persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")

    payload = json.loads(rec.body)
    validate_payload(payload)  # must validate against vendor/swe-schemas pinned schema
