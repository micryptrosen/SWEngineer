from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _snapshot(repo: Path) -> dict | None:
    p = (repo / "tests" / "_snapshots" / "phase3c_selection.json").resolve()
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def test_phase3e_parity_probe_reports_selection_block() -> None:
    repo = _repo_root()
    tool = repo / "tools" / "swengineer.ps1"
    assert tool.exists(), f"missing tool entrypoint: {tool}"

    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(tool),
            "parity-probe",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert r.returncode in (0, 2), f"unexpected rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"

    obj = json.loads(r.stdout)
    assert obj.get("kind") == "swengineer-parity-probe"
    assert int(obj.get("version", 0)) == 1

    sel = obj.get("selection")
    assert isinstance(sel, dict), f"missing selection block: {sel}"
    assert sel.get("runner_mod"), "selection.runner_mod missing/empty"
    assert sel.get("surface_mod"), "selection.surface_mod missing/empty"

    snap = _snapshot(repo)
    if snap is not None:
        # Must match frozen snapshot when present
        assert sel.get("source") == "snapshot"
        assert sel.get("runner_mod") == snap["runner_mod"]
        assert sel.get("surface_mod") == snap["surface_mod"]

