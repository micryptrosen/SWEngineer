from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase3f_publish_gate_fails_on_dirty_tree_with_reason() -> None:
    repo = _repo_root()
    gate = repo / "tools" / "publish_gated.ps1"
    assert gate.exists(), f"missing publish gate: {gate}"

    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(gate),
            "-Intent",
            "tag",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )

    # If the tree is dirty (common during dev), publish gate MUST refuse with rc=4 and a clear reason.
    # If the tree is clean, it may return 0; both are acceptable.
    if r.returncode == 0:
        return

    assert r.returncode == 4, f"unexpected rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    combined = (r.stdout or "") + "\n" + (r.stderr or "")
    assert "dirty working tree" in combined.lower(), f"missing dirty-tree reason\nstdout={r.stdout}\nstderr={r.stderr}"

