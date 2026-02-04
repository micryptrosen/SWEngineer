from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here.parent, *here.parents):
        if (p / "pyproject.toml").exists() and (p / "src").exists() and (p / "tools").exists():
            return p
    raise RuntimeError("could not locate repo root")


def test_phase3a_swengineer_module_tool_parity_probe_smoke() -> None:
    repo = _repo_root()
    tool = repo / "tools" / "swengineer_module.ps1"
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
    assert isinstance(obj, dict), f"expected object JSON, got {type(obj)}"

    # New fields (optional for backward compatibility; should be present after Phase3B)
    if "kind" in obj:
        assert obj["kind"] == "swengineer-parity-probe"
    if "version" in obj:
        assert obj["version"] == 1

    assert "expected_vendor_schema_root" in obj
    assert "probe_rc" in obj
    assert "probe" in obj and isinstance(obj["probe"], dict)

    expected = Path(obj["expected_vendor_schema_root"]).resolve()
    got = Path(obj["probe"]["schema_root"]).resolve()
    assert got == expected, f"SCHEMA_ROOT drift: got={got} expected={expected}"

