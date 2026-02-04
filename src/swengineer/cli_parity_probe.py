from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


KIND = "swengineer-parity-probe"
VERSION = 1

SURFACE_TOKENS_DEFAULT = ["planner", "plan", "planning", "validate", "validator", "validation", "schema", "schemas"]


def _repo_root() -> Path:
    # src/swengineer/ -> repo
    return Path(__file__).resolve().parents[2]


def _src_root(repo: Path) -> Path:
    return (repo / "src").resolve()


def _vendor_schema_root(repo: Path) -> Path:
    return (repo / "vendor" / "swe-schemas").resolve()


def _snapshot_path(repo: Path) -> Path:
    return (repo / "tests" / "_snapshots" / "phase3c_selection.json").resolve()


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def _iter_py_files(src_root: Path) -> List[Path]:
    files: List[Path] = []
    for p in src_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        files.append(p)
    files.sort(key=lambda x: x.relative_to(src_root).as_posix().lower())
    return files


def _collect_candidates(src_root: Path, tokens: List[str], limit: int = 12) -> List[Tuple[str, str]]:
    toks = [t.lower() for t in tokens]
    out: List[Tuple[str, str]] = []
    for p in _iter_py_files(src_root):
        rel = p.relative_to(src_root).as_posix()
        rel_lower = rel.lower()
        if not any(t in rel_lower for t in toks):
            continue
        txt = _read_text(p)
        if ("swe_schemas" not in txt) and ("resolve_schema_root" not in txt):
            continue
        mod = rel[:-3].replace("/", ".")
        out.append((mod, rel))
        if len(out) >= limit:
            break
    return out


def _select_from_snapshot_or_discovery(repo: Path) -> Dict[str, Any]:
    """
    Returns:
      {
        "source": "snapshot"|"discovery",
        "runner_mod": str,
        "surface_mod": str,
        "runner_rel": str|None,
        "surface_rel": str|None,
        "surface_tokens": List[str],
        "snapshot_path": str|None
      }
    """
    src_root = _src_root(repo)
    snap_path = _snapshot_path(repo)

    surface_tokens = SURFACE_TOKENS_DEFAULT
    runner_mod: Optional[str] = None
    surface_mod: Optional[str] = None
    runner_rel: Optional[str] = None
    surface_rel: Optional[str] = None

    if snap_path.exists():
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
        surface_tokens = [str(x).lower() for x in snap.get("surface_tokens", surface_tokens)]
        runner_mod = snap.get("runner_mod")
        surface_mod = snap.get("surface_mod")
        runner_rel = snap.get("runner_rel")
        surface_rel = snap.get("surface_rel")
        if runner_mod and surface_mod:
            return {
                "source": "snapshot",
                "runner_mod": runner_mod,
                "surface_mod": surface_mod,
                "runner_rel": runner_rel,
                "surface_rel": surface_rel,
                "surface_tokens": surface_tokens,
                "snapshot_path": str(snap_path),
            }

    # Discovery fallback (still deterministic; lexicographic first-hit)
    runners = _collect_candidates(src_root, ["runner"], limit=8)
    surfaces = _collect_candidates(src_root, surface_tokens, limit=16)
    surfaces = [(m, r) for (m, r) in surfaces if ".runner." not in ("." + m + ".")]

    if runners:
        runner_mod, runner_rel = runners[0]
    if surfaces:
        surface_mod, surface_rel = surfaces[0]

    return {
        "source": "discovery",
        "runner_mod": runner_mod or "",
        "surface_mod": surface_mod or "",
        "runner_rel": runner_rel,
        "surface_rel": surface_rel,
        "surface_tokens": surface_tokens,
        "snapshot_path": str(snap_path) if snap_path.exists() else None,
    }


def _run_isolated_probe(repo: Path, selection: Dict[str, Any]) -> Dict[str, Any]:
    src_root = _src_root(repo)
    vendor_root = _vendor_schema_root(repo)

    runner_mod = str(selection.get("runner_mod") or "")
    surface_mod = str(selection.get("surface_mod") or "")

    # Provide candidate lists in output for debugging even when selection is snapshot-driven
    runner_candidates = [runner_mod] if runner_mod else [m for (m, _) in _collect_candidates(src_root, ["runner"], limit=8)]
    surface_candidates = [surface_mod] if surface_mod else [m for (m, _) in _collect_candidates(src_root, selection.get("surface_tokens", SURFACE_TOKENS_DEFAULT), limit=16)]

    code = r"""
import json, os, sys
from pathlib import Path

repo = Path(os.environ["SWENG_REPO"]).resolve()
src_root = (repo / "src").resolve()
sys.path.insert(0, str(src_root))

runner_mod = os.environ.get("SWENG_RUNNER_MOD","")
surface_mod = os.environ.get("SWENG_SURFACE_MOD","")

def try_import(mod: str):
    if not mod:
        return {"mod": mod, "ok": False, "err": "empty-module"}
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

    out: Dict[str, Any] = {
        # Self-describing envelope
        "kind": KIND,
        "version": VERSION,

        # Repo context
        "repo": str(repo),
        "src_root": str(src_root),
        "expected_vendor_schema_root": str(vendor_root),

        # NEW: selection block
        "selection": {
            "source": selection.get("source"),
            "snapshot_path": selection.get("snapshot_path"),
            "runner_mod": runner_mod,
            "surface_mod": surface_mod,
            "runner_rel": selection.get("runner_rel"),
            "surface_rel": selection.get("surface_rel"),
            "surface_tokens": selection.get("surface_tokens"),
        },

        # Existing fields (preserved)
        "runner_candidates": runner_candidates,
        "surface_candidates": surface_candidates,
        "probe_rc": r.returncode,
        "probe_stdout": r.stdout.strip(),
        "probe_stderr": r.stderr.strip(),
    }

    if r.returncode != 0:
        return out

    try:
        parsed = json.loads(r.stdout.strip())
    except Exception as e:
        out["parse_error"] = repr(e)
        return out

    out["probe"] = parsed
    return out


def _write_artifact_json(out_path: Path, obj: Dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    out_path.write_text(txt, encoding="utf-8")


def _write_sha256_sidecar(target_path: Path) -> Path:
    data = target_path.read_bytes()
    h = hashlib.sha256()
    h.update(data)
    digest = h.hexdigest()
    sidecar = target_path.with_suffix(target_path.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {target_path.name}\n", encoding="utf-8")
    return sidecar


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="swengineer parity-probe", add_help=True)
    ap.add_argument("--out", type=str, default="", help="write JSON report to path and emit .sha256 sidecar")
    args = ap.parse_args(argv)

    repo = _repo_root()
    selection = _select_from_snapshot_or_discovery(repo)
    report = _run_isolated_probe(repo, selection)

    # Always emit JSON to stdout
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = (repo / out_path).resolve()
        _write_artifact_json(out_path, report)
        _write_sha256_sidecar(out_path)

    return 0 if report.get("probe_rc") == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

