from __future__ import annotations

import json
from pathlib import Path

from app.gui.planner import (
    GuiStore,
    make_approval,
    make_run_plan,
    persist_approval,
    persist_handoff_from_plan,
    persist_run_plan,
)
from app.validation.canonical import verify_payload_sha256, compute_payload_sha256


def test_run_handoff_payload_sha256_verifies(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)

    handoff_rec = persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")
    payload = json.loads(handoff_rec.body)

    assert payload["contract"] == "run_handoff/1.0"
    assert verify_payload_sha256(payload) is True


def test_payload_sha256_fails_on_mutation(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)

    handoff_rec = persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")
    payload = json.loads(handoff_rec.body)

    assert verify_payload_sha256(payload) is True

    payload["runner_label"] = "MUTATED"
    assert verify_payload_sha256(payload) is False


def test_compute_payload_sha256_is_order_invariant() -> None:
    a = {"contract": "x/1.0", "b": 2, "a": 1}
    b = {"a": 1, "b": 2, "contract": "x/1.0"}
    assert compute_payload_sha256(a) == compute_payload_sha256(b)
