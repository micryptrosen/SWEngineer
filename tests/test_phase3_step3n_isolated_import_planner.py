from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_isolated_python_can_import_planner_after_bootstrap() -> None:
    """
    Phase 3 / Step 3N contract:
    Under `python -I`, we can import app.gui.planner after applying swe_bootstrap,
    with src-layout discoverability and without relying on ambient sys.path.
    """
    root = _repo_root()

    code = r"""
import sys
from pathlib import Path

root = Path(r"{ROOT}").resolve()
src = (root / "src").resolve()
sys.path.insert(0, str(src))

import swe_bootstrap
swe_bootstrap.apply()

import app.gui.planner as planner
print("PLANNER_IMPORT=OK")
""".replace("{ROOT}", str(root))

    out = subprocess.check_output([sys.executable, "-I", "-c", code], text=True).strip()
    assert "PLANNER_IMPORT=OK" in out
