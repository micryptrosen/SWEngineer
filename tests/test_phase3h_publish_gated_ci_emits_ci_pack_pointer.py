from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase3h_publish_gated_ci_emits_ci_pack_pointer_when_clean() -> None:
    repo = _repo_root()
    tool = repo / "tools" / "publish_gated_ci.ps1"
    assert tool.exists(), f"missing wrapper: {tool}"

    try:
        r = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(tool),
                "-Intent",
                "tag",
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "").strip()
        err = (e.stderr or "").strip()
        raise AssertionError(
            "FAILURE DETECTED: publish_gated_ci subprocess timed out (60s)\n"
            f"stdout={out}\n"
            f"stderr={err}\n"
        ) from e

    # If repo is dirty, publish gate will refuse with rc=4, and wrapper must propagate rc.
    assert r.returncode in (0, 4), f"unexpected rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"

    lines = (r.stdout or "").splitlines()
    ptr_lines = [ln for ln in lines if ln.startswith("PUBLISH_CI_PACK_DIR=")]

    if r.returncode == 0:
        assert ptr_lines, f"missing PUBLISH_CI_PACK_DIR line\nstdout={r.stdout}\nstderr={r.stderr}"
        p = Path(ptr_lines[-1].split("=", 1)[1].strip())
        assert p.exists(), f"ci pack dir missing: {p}"
    else:
        # Dirty-tree refusal is allowed; pointer is not required.
        assert not ptr_lines, "pointer must not be emitted when publish gate refused (dirty tree)"

