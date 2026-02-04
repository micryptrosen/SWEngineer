from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase3f_publish_gate_enforces_parity_probe_selection_block() -> None:
    repo = _repo_root()
    tool = repo / "tools" / "publish_gated.ps1"
    assert tool.exists(), f"missing publish gate: {tool}"

    # The gate requires a clean tree; this test only asserts that, when it runs far enough
    # to write parity evidence, the file contains selection fields. If tree is dirty, gate will fail earlier.
    # Therefore we invoke parity-probe directly and assert selection is present (publish gate reads same file).
    entry = repo / "tools" / "swengineer.ps1"
    assert entry.exists(), f"missing tool entrypoint: {entry}"

    out = repo / "_evidence" / "publish" / "_test_parity_probe_selection.json"

    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(entry),
            "parity-probe",
            "-Out",
            str(out),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert r.returncode in (0, 2), f"unexpected rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    assert out.exists(), "missing parity-probe out"
    obj = json.loads(out.read_text(encoding="utf-8"))
    sel = obj.get("selection")
    assert isinstance(sel, dict), f"missing selection block: {sel}"
    assert sel.get("runner_mod"), "selection.runner_mod missing/empty"
    assert sel.get("surface_mod"), "selection.surface_mod missing/empty"

    snap_path = (repo / "tests" / "_snapshots" / "phase3c_selection.json").resolve()
    if snap_path.exists():
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
        assert sel.get("runner_mod") == snap["runner_mod"]
        assert sel.get("surface_mod") == snap["surface_mod"]

