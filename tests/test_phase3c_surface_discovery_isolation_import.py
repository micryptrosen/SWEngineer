from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src_root(repo: Path) -> Path:
    return (repo / "src").resolve()


def _vendor_schema_root(repo: Path) -> Path:
    return (repo / "vendor" / "swe-schemas").resolve()


def _snapshot_path(repo: Path) -> Path:
    return (repo / "tests" / "_snapshots" / "phase3c_selection.json").resolve()


def _iter_py_files(src_root: Path) -> List[Path]:
    files: List[Path] = []
    for p in src_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        files.append(p)
    files.sort(key=lambda x: x.relative_to(src_root).as_posix().lower())
    return files


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def _is_surface_path(rel_lower: str, tokens: List[str]) -> bool:
    return any(t in rel_lower for t in tokens)


def _discover_surface_candidates(src_root: Path, tokens: List[str], limit: int = 25) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for p in _iter_py_files(src_root):
        rel = p.relative_to(src_root).as_posix()
        rel_lower = rel.lower()
        if not _is_surface_path(rel_lower, tokens):
            continue
        txt = _read_text(p)
        if ("swe_schemas" not in txt) and ("resolve_schema_root" not in txt):
            continue
        mod = rel[:-3].replace("/", ".")
        out.append((mod, rel))
        if len(out) >= limit:
            break
    return out


def _discover_runner_candidates(src_root: Path, limit: int = 10) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for p in _iter_py_files(src_root):
        rel = p.relative_to(src_root).as_posix()
        rel_lower = rel.lower()
        if "runner" not in rel_lower:
            continue
        txt = _read_text(p)
        if ("swe_schemas" not in txt) and ("resolve_schema_root" not in txt):
            continue
        mod = rel[:-3].replace("/", ".")
        out.append((mod, rel))
        if len(out) >= limit:
            break
    return out


def test_phase3c_surface_discovery_and_isolation_import_lock() -> None:
    """
    Phase3C(A)+Phase3D(A) contract:
    - Discovery algorithm exists (token-based, no folder assumptions).
    - Selection is FROZEN via tests/_snapshots/phase3c_selection.json:
        - runner_mod + surface_mod must remain stable unless snapshot is intentionally regenerated.
    - Under python -I with explicit src injection:
        - importing selected runner module succeeds
        - importing selected surface module succeeds
        - swe_schemas.resolve_schema_root() == <repo>/vendor/swe-schemas
    """
    repo = _repo_root()
    src_root = _src_root(repo)
    vendor_root = _vendor_schema_root(repo)

    assert src_root.exists(), f"missing src root: {src_root}"
    assert vendor_root.exists(), f"missing vendor schema root: {vendor_root}"

    snap_path = _snapshot_path(repo)
    assert snap_path.exists(), (
        f"missing selection snapshot: {snap_path}. "
        "Run tools/_gen_phase3d_selection_snapshot.py to regenerate intentionally."
    )
    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    assert snap.get("selection_kind") == "phase3c-surface-selection"
    assert int(snap.get("selection_version", 0)) == 1

    surface_tokens = [str(x).lower() for x in snap.get("surface_tokens", [])]
    assert surface_tokens, "snapshot missing surface_tokens"

    surfaces = _discover_surface_candidates(src_root, surface_tokens)
    runners = _discover_runner_candidates(src_root)

    assert runners, "No runner-ish candidates discovered under src/"
    assert surfaces, "No surface candidates discovered under src/"

    runner_mod = runners[0][0]
    surface_mod = surfaces[0][0]

    # Stability lock
    assert runner_mod == snap["runner_mod"], f"runner selection drift: got={runner_mod} expected={snap['runner_mod']}"
    assert surface_mod == snap["surface_mod"], f"surface selection drift: got={surface_mod} expected={snap['surface_mod']}"

    code = r"""
import json, os, sys
from pathlib import Path

repo = Path(os.environ["SWENG_REPO"]).resolve()
src_root = (repo / "src").resolve()
sys.path.insert(0, str(src_root))

runner_mod = os.environ["SWENG_RUNNER_MOD"]
surface_mod = os.environ["SWENG_SURFACE_MOD"]

def try_import(mod: str):
    try:
        __import__(mod)
        return {"mod": mod, "ok": True, "err": None}
    except Exception as e:
        return {"mod": mod, "ok": False, "err": repr(e)}

from swe_schemas import resolve_schema_root  # type: ignore

out = {
  "schema_root": str(resolve_schema_root()),
  "runner": try_import(runner_mod),
  "surface": try_import(surface_mod),
}
print(json.dumps(out, sort_keys=True))
"""

    env = dict(os.environ)
    env["SWENG_REPO"] = str(repo)
    env["SWENG_RUNNER_MOD"] = runner_mod
    env["SWENG_SURFACE_MOD"] = surface_mod

    r = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
    )

    assert r.returncode == 0, f"isolation probe failed rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    obj = json.loads(r.stdout.strip())

    got = Path(obj["schema_root"]).resolve()
    expected = vendor_root.resolve()
    assert got == expected, f"SCHEMA_ROOT drift: got={got} expected={expected}"

    assert obj["runner"]["ok"] is True, f"runner import failed: {obj['runner']}"
    assert obj["surface"]["ok"] is True, f"surface import failed: {obj['surface']}"

