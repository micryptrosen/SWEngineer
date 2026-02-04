from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase2d_cli_parity_probe_smoke() -> None:
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

    # tool returns 0 if probe ran, 2 if probe rc != 0. Either way stdout must be JSON.
    assert r.returncode in (0, 2), f"unexpected rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    obj = json.loads(r.stdout)
    assert "repo" in obj
    assert "probe_rc" in obj

