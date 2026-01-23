from pathlib import Path

from app.gui.planner import (
    clone_run_plan,
    make_run_plan,
    make_superseded,
    persist_run_plan,
    persist_superseded,
)
from app.gui.store import GuiStore


def test_clone_plan_and_supersede_marker(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    prior = persist_run_plan(s, plan)

    new_plan = clone_run_plan(s, prior_plan_rec=prior, new_notes="n2")
    marker = make_superseded(prior.ev_id, new_plan.ev_id, reason="test")
    persist_superseded(s, marker)

    ev = s.read_evidence()
    assert len(ev) == 3
    assert ev[0].kind == "RUN_PLAN"
    assert ev[1].kind == "RUN_PLAN"
    assert ev[2].kind == "RUN_PLAN_SUPERSEDED"
    assert prior.ev_id in ev[1].body
    assert prior.ev_id in ev[2].body
    assert new_plan.ev_id in ev[2].body
