from __future__ import annotations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

TARGETS = [
    Path("app/gui/main.py"),
    Path("app/main.py"),
    Path("phase_2d_build.py"),
    Path("phase_2c_runner_parity.py"),
    Path("phase_2c_chain_hardening.py"),
]

def test_entrypoints_call_swe_bootstrap_apply():
    missing = []
    for rel in TARGETS:
        p = REPO / rel
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        ok = ("import swe_bootstrap as _swe_bootstrap" in t) and ("_swe_bootstrap.apply()" in t)
        if not ok:
            missing.append(str(rel).replace("\\", "/"))
    assert not missing, "Missing bootstrap wiring in: " + ", ".join(missing)
