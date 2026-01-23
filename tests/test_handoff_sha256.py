import hashlib
import json
from pathlib import Path

from app.gui.planner import (
    make_approval,
    make_run_plan,
    persist_approval,
    persist_handoff_from_plan,
    persist_run_plan,
)
from app.gui.store import GuiStore


def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def test_handoff_includes_valid_sha256(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(
        plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok"
    )
    persist_approval(s, appr)

    handoff_rec = persist_handoff_from_plan(
        s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note"
    )

    obj = json.loads(handoff_rec.body)
    assert obj["contract"] == "run_handoff/1.0"
    assert obj["plan_ev_id"] == plan_rec.ev_id
    assert obj["runner_label"] == "TEST_RUNNER"
    assert obj["payload_sha256"]

    # Recompute hash from the exact payload fields (excluding payload_sha256)
    payload_no_sha = dict(obj)
    payload_no_sha.pop("payload_sha256", None)
    canon = _canonical_json(payload_no_sha)
    sha = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    assert sha == obj["payload_sha256"]
