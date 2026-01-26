from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_isolated_python_e2e_planner_handoff_validation() -> None:
    """
    Phase 3 / Step 3O contract:
    Under `python -I`, we can:
      - inject src into sys.path
      - apply bootstrap
      - import GUI planner
      - generate plan + approval + handoff into a temp dir
      - validate handoff payload under vendor schemas (no fallback)
    """
    root = _repo_root()

    code = r"""
import sys
from pathlib import Path
import tempfile

root = Path(r"{ROOT}").resolve()
src = (root / "src").resolve()
sys.path.insert(0, str(src))

import swe_bootstrap
swe_bootstrap.apply()

from app.gui.planner import (
  GuiStore,
  make_run_plan, persist_run_plan,
  make_approval, persist_approval,
  persist_handoff_from_plan,
)

with tempfile.TemporaryDirectory() as td:
    s = GuiStore(base_dir=Path(td))
    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)
    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)
    handoff_rec = persist_handoff_from_plan(s, plan_rec, runner_label="ISO_RUNNER", notes="iso")
    # If we got here, schema validation passed under vendor root.
    print("E2E_OK=" + handoff_rec.ev_id)
""".replace("{ROOT}", str(root))

    out = subprocess.check_output([sys.executable, "-I", "-c", code], text=True).strip()
    assert "E2E_OK=" in out
