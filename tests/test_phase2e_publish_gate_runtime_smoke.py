from __future__ import annotations

from pathlib import Path
import subprocess


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase2e_publish_gate_runtime_smoke() -> None:
    repo = _repo_root()
    script = repo / "tools" / "publish_gated.ps1"
    assert script.exists(), f"missing publish gate: {script}"

    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Intent",
            "tag",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )

    out = (r.stdout or "") + (r.stderr or "")

    # Two acceptable outcomes:
    # 1) GREEN (clean tree + tests + parity-probe all pass)
    # 2) Deterministic failure with explicit FAILURE DETECTED messaging (dirty tree is common during dev)
    if r.returncode == 0:
        assert "PUBLISH_GATED=GREEN" in out
        return

    assert "FAILURE DETECTED:" in out, f"publish gate failed but did not emit deterministic failure text:\n{out}"

