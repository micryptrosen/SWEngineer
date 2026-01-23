from pathlib import Path

from app.gui.planner import make_run_plan, persist_run_plan
from app.gui.store import GuiStore


def test_run_plan_persists(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n")
    rec = persist_run_plan(s, plan)

    ev = s.read_evidence()
    assert len(ev) == 1
    assert ev[0].kind == "RUN_PLAN"
    assert rec.ev_id == ev[0].ev_id
