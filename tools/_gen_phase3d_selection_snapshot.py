from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

SELECTION_VERSION = 1

SURFACE_TOKENS = ("planner", "plan", "planning", "validate", "validator", "validation", "schema", "schemas")

def repo_root() -> Path:
    # tools/ -> repo
    return Path(__file__).resolve().parents[1]

def src_root(repo: Path) -> Path:
    return (repo / "src").resolve()

def iter_py_files(src: Path) -> List[Path]:
    files: List[Path] = []
    for p in src.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        files.append(p)
    files.sort(key=lambda x: x.relative_to(src).as_posix().lower())
    return files

def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")

def is_surface_path(rel_lower: str) -> bool:
    return any(t in rel_lower for t in SURFACE_TOKENS)

def discover_surface_candidates(src: Path, limit: int = 25) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for p in iter_py_files(src):
        rel = p.relative_to(src).as_posix()
        rel_lower = rel.lower()
        if not is_surface_path(rel_lower):
            continue
        txt = read_text(p)
        if ("swe_schemas" not in txt) and ("resolve_schema_root" not in txt):
            continue
        mod = rel[:-3].replace("/", ".")
        out.append((mod, rel))
        if len(out) >= limit:
            break
    return out

def discover_runner_candidates(src: Path, limit: int = 10) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for p in iter_py_files(src):
        rel = p.relative_to(src).as_posix()
        rel_lower = rel.lower()
        if "runner" not in rel_lower:
            continue
        txt = read_text(p)
        if ("swe_schemas" not in txt) and ("resolve_schema_root" not in txt):
            continue
        mod = rel[:-3].replace("/", ".")
        out.append((mod, rel))
        if len(out) >= limit:
            break
    return out

def main() -> int:
    repo = repo_root()
    src = src_root(repo)
    if not src.exists():
        raise SystemExit(f"missing src root: {src}")

    surfaces = discover_surface_candidates(src)
    runners = discover_runner_candidates(src)

    if not runners:
        raise SystemExit("no runner candidates discovered")
    if not surfaces:
        raise SystemExit("no surface candidates discovered")

    runner_mod, runner_rel = runners[0]
    surface_mod, surface_rel = surfaces[0]

    snap = {
        "selection_kind": "phase3c-surface-selection",
        "selection_version": SELECTION_VERSION,
        "runner_mod": runner_mod,
        "runner_rel": runner_rel,
        "surface_mod": surface_mod,
        "surface_rel": surface_rel,
        "surface_tokens": list(SURFACE_TOKENS),
        "rules": {
            "runner_path_contains": "runner",
            "file_must_reference": ["swe_schemas OR resolve_schema_root"],
            "surface_path_contains_any": list(SURFACE_TOKENS),
            "surface_excludes_runner_module": True,
            "ordering": "lexicographic by rel path",
            "pick": "first runner + first surface",
        },
    }

    out_dir = repo / "tests" / "_snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "phase3c_selection.json"
    out_path.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

