from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable, List


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_py_files(src_root: Path) -> Iterable[Path]:
    for p in src_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def _to_module(src_root: Path, py_file: Path) -> str:
    rel = py_file.relative_to(src_root).as_posix()
    if not rel.endswith(".py"):
        raise RuntimeError(f"not a .py file: {py_file}")
    return rel[:-3].replace("/", ".")


def _collect_candidates(src_root: Path, tokens: List[str], limit: int = 8) -> List[str]:
    """
    Deterministically collect module candidates whose *path* contains any token.
    Returns module names like 'swengineer.runner.exec'.
    """
    toks = [t.lower() for t in tokens]
    files: List[Path] = []
    for p in _iter_py_files(src_root):
        rel_lower = p.relative_to(src_root).as_posix().lower()
        if any(t in rel_lower for t in toks):
            files.append(p)

    files.sort(key=lambda x: x.relative_to(src_root).as_posix().lower())

    mods: List[str] = []
    for p in files:
        mods.append(_to_module(src_root, p))
        if len(mods) >= limit:
            break
    return mods


def _run_isolated_probe(repo: Path, runner_mods: List[str], surface_mods: List[str]) -> dict:
    """
    Launch python -I and:
      - inject <repo>/src into sys.path
      - report schema_root
      - attempt imports of runner + planning/validation surface modules
    Returns parsed JSON dict.
    """
    code = r"""
import json, os, sys
from pathlib import Path

repo = Path(os.environ["SWENG_REPO"]).resolve()
src_root = (repo / "src").resolve()
sys.path.insert(0, str(src_root))

from swe_schemas import resolve_schema_root  # type: ignore

runner_mods = json.loads(os.environ["SWENG_RUNNER_MODS"])
surface_mods = json.loads(os.environ["SWENG_SURFACE_MODS"])

def try_import(mod: str):
    try:
        __import__(mod)
        return {"mod": mod, "ok": True, "err": None}
    except Exception as e:
        return {"mod": mod, "ok": False, "err": repr(e)}

out = {
    "schema_root": str(resolve_schema_root()),
    "runner": [try_import(m) for m in runner_mods],
    "surface": [try_import(m) for m in surface_mods],
}

print(json.dumps(out, sort_keys=True))
"""

    env = dict(os.environ)
    env["SWENG_REPO"] = str(repo)
    env["SWENG_RUNNER_MODS"] = json.dumps(runner_mods)
    env["SWENG_SURFACE_MODS"] = json.dumps(surface_mods)

    r = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
    )

    if r.returncode != 0:
        raise AssertionError(
            "python -I probe failed\n"
            f"rc={r.returncode}\n"
            f"stdout={r.stdout}\n"
            f"stderr={r.stderr}"
        )

    try:
        return json.loads(r.stdout.strip())
    except Exception as e:
        raise AssertionError(
            "python -I probe did not return valid JSON\n"
            f"err={repr(e)}\n"
            f"stdout={r.stdout}\n"
            f"stderr={r.stderr}"
        )


def test_phase2b_runner_planning_parity_under_isolation() -> None:
    """
    Phase2B(A) parity probe (corrected):
    - Under python -I with explicit src injection:
        - at least one runner module imports successfully
        - at least one planning/validation surface module imports successfully
    - Schema root under the same isolated session resolves to <repo>/vendor/swe-schemas.
    """
    repo = _repo_root()
    src_root = (repo / "src").resolve()
    vendor_root = (repo / "vendor" / "swe-schemas").resolve()

    assert src_root.exists(), f"missing src root: {src_root}"
    assert vendor_root.exists(), f"missing vendor schema root: {vendor_root}"

    runner_mods = _collect_candidates(src_root, tokens=["runner"], limit=8)

    # “planner” may not exist as a directory name. We look for planning/validation surfaces by common tokens.
    surface_tokens = ["planner", "plan", "planning", "validate", "validator", "validation", "schema", "schemas"]
    surface_mods = _collect_candidates(src_root, tokens=surface_tokens, limit=12)

    # Ensure we don't accidentally satisfy surface via runner-only paths
    surface_mods = [m for m in surface_mods if ".runner." not in ("." + m + ".")]

    assert runner_mods, "No runner candidates found under src/ for Phase2B parity probe"
    assert surface_mods, (
        "No planning/validation surface candidates found under src/ for Phase2B parity probe. "
        "Searched tokens: planner|plan|planning|validate|validator|validation|schema|schemas"
    )

    out = _run_isolated_probe(repo, runner_mods, surface_mods)

    schema_root = Path(out["schema_root"]).resolve()
    assert schema_root == vendor_root, f"schema_root drift under -I: got={schema_root} expected={vendor_root}"

    runner_ok = [x for x in out["runner"] if x.get("ok") is True]
    surface_ok = [x for x in out["surface"] if x.get("ok") is True]

    assert runner_ok, f"No runner modules importable under -I. Results={out['runner']}"
    assert surface_ok, f"No planning/validation surface modules importable under -I. Results={out['surface']}"

