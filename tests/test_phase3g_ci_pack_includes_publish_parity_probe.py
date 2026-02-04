from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase3g_ci_pack_bundles_publish_parity_probe_when_present(tmp_path: Path) -> None:
    repo = _repo_root()
    tool = repo / "tools" / "ci_pack.ps1"
    assert tool.exists(), f"missing ci pack tool: {tool}"

    # Ensure publish parity exists (create it via parity-probe -Out into _evidence/publish/)
    publish_dir = repo / "_evidence" / "publish"
    publish_dir.mkdir(parents=True, exist_ok=True)
    publish_json = publish_dir / "parity_probe.json"

    entry = repo / "tools" / "swengineer.ps1"
    r0 = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(entry),
            "parity-probe",
            "-Out",
            str(publish_json),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert r0.returncode in (0, 2), f"unexpected rc={r0.returncode}\nstdout={r0.stdout}\nstderr={r0.stderr}"
    assert publish_json.exists(), "missing publish parity_probe.json"

    # Run ci_pack but skip pytest to avoid nested pytest deadlocks under pytest
    env = dict(os.environ)
    env["SWENG_CI_PACK_SKIP_PYTEST"] = "1"

    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(tool),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, f"ci_pack rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"

    # Canonical token from Phase2H contract
    bundle = None
    for line in (r.stdout or "").splitlines():
        if line.startswith("CI_PACK_EVIDENCE_DIR="):
            bundle = Path(line.split("=", 1)[1].strip())
            break
    assert bundle is not None, f"missing CI_PACK_EVIDENCE_DIR line\nstdout={r.stdout}\nstderr={r.stderr}"
    assert bundle.exists(), f"bundle path missing: {bundle}"

    bundled = bundle / "publish" / "parity_probe.json"
    bundled_sha = bundle / "publish" / "parity_probe.json.sha256"
    assert bundled.exists(), "bundle missing publish/parity_probe.json"
    assert bundled_sha.exists(), "bundle missing publish/parity_probe.json.sha256"

