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

REQUIRED_SNIPPETS = [
    "def _swe_find_repo_root",
    "_SRC = _REPO / 'src'",
    "_VENDOR = _REPO / 'vendor' / 'swe-schemas'",
    "import swe_bootstrap as _swe_bootstrap",
    "_swe_bootstrap.apply()",
]

def test_entrypoints_have_script_safe_bootstrap():
    missing = []
    for rel in TARGETS:
        p = REPO / rel
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        ok = all(s in t for s in REQUIRED_SNIPPETS)
        if not ok:
            missing.append(str(rel).replace("\\", "/"))
    assert not missing, "EntryPoint bootstrap not script-safe in: " + ", ".join(missing)
