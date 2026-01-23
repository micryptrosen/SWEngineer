from pathlib import Path

from app.gui.planner import make_approval, make_run_plan, persist_approval, persist_run_plan
from app.gui.store import GuiStore


def test_run_plan_approval_persists(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(
        plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok"
    )
    persist_approval(s, appr)

    ev = s.read_evidence()
    assert len(ev) == 2
    assert ev[0].kind == "RUN_PLAN"
    assert ev[1].kind == "RUN_PLAN_APPROVAL"
    assert plan_rec.ev_id in ev[1].body
