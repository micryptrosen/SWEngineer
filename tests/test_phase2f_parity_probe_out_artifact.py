from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_newline_terminated(p: Path) -> bool:
    b = p.read_bytes()
    return len(b) > 0 and b.endswith(b"\n")


def test_phase2f_parity_probe_out_writes_json_and_sha256(tmp_path: Path) -> None:
    repo = _repo_root()
    tool = repo / "tools" / "swengineer.ps1"
    assert tool.exists(), f"missing tool entrypoint: {tool}"

    out = tmp_path / "parity_report.json"

    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(tool),
            "parity-probe",
            "-Out",
            str(out),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert r.returncode in (0, 2), f"unexpected rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"

    assert out.exists(), f"missing report: {out}"
    assert _is_newline_terminated(out), "report JSON must be newline-terminated"

    sidecar = Path(str(out) + ".sha256")
    assert sidecar.exists(), f"missing sidecar: {sidecar}"
    assert _is_newline_terminated(sidecar), "sha256 sidecar must be newline-terminated"

    data = out.read_bytes()
    digest = hashlib.sha256(data).hexdigest()

    line = sidecar.read_text(encoding="utf-8").strip()
    parts = line.split()
    assert parts and parts[0] == digest, f"sha256 mismatch: got={parts[0] if parts else ''} expected={digest}"

