from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, List


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_py_files(src_root: Path) -> Iterable[Path]:
    for p in src_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="strict")


def _token_hit(txt: str) -> bool:
    return ("resolve_schema_root" in txt) or ("from swe_schemas" in txt) or ("import swe_schemas" in txt)


def _collect_candidates(src_root: Path, path_tokens: List[str], *, exclude_tokens: List[str] | None = None) -> List[Path]:
    toks = [t.lower() for t in path_tokens]
    ex = [t.lower() for t in (exclude_tokens or [])]
    hits: List[Path] = []
    for p in _iter_py_files(src_root):
        rel = p.relative_to(src_root).as_posix()
        rel_lower = rel.lower()
        if any(t in rel_lower for t in ex):
            continue
        if any(t in rel_lower for t in toks):
            hits.append(p)
    hits.sort(key=lambda x: x.relative_to(src_root).as_posix().lower())
    return hits


def _first_binding_module(src_root: Path, candidates: List[Path]) -> Path | None:
    for p in candidates:
        if _token_hit(_read_text(p)):
            return p
    return None


def _is_allowed_runner_wrapper(rel_posix: str) -> bool:
    return rel_posix.replace("\\", "/") == "swe_runner/__init__.py"


def _is_allowed_schema_owner(rel_posix: str) -> bool:
    # In this repo, swe_schemas is a src package; it is the canonical owner.
    rel = rel_posix.replace("\\", "/")
    return rel.startswith("swe_schemas/")


def _wrapper_delegates_to_swe_schemas(tree: ast.AST) -> bool:
    """
    Required form for the swe_runner wrapper:
      import swe_schemas; return swe_schemas.resolve_schema_root()
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_schema_root":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Call):
                    call = sub.value
                    if isinstance(call.func, ast.Attribute) and call.func.attr == "resolve_schema_root":
                        if isinstance(call.func.value, ast.Name) and call.func.value.id == "swe_schemas":
                            return True
    return False


def _assert_no_local_resolver_clones_except_allowed(src_root: Path) -> None:
    offenders: List[str] = []
    wrapper_bad: List[str] = []

    for p in _iter_py_files(src_root):
        rel = p.relative_to(src_root).as_posix()
        txt = _read_text(p)

        if "resolve_schema_root" not in txt:
            continue

        try:
            tree = ast.parse(txt)
        except SyntaxError:
            raise AssertionError(f"SyntaxError parsing {rel}")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "resolve_schema_root":
                if _is_allowed_schema_owner(rel):
                    # swe_schemas owns it; always allowed
                    continue
                if _is_allowed_runner_wrapper(rel):
                    if not _wrapper_delegates_to_swe_schemas(tree):
                        wrapper_bad.append(rel)
                else:
                    offenders.append(rel)

            if isinstance(node, ast.AsyncFunctionDef) and node.name == "resolve_schema_root":
                if _is_allowed_schema_owner(rel):
                    continue
                offenders.append(rel)

    assert not offenders, (
        "Local resolver clones detected under src/ (forbidden). "
        "Allowed owners: src/swe_schemas/** and wrapper src/swe_runner/__init__.py only. "
        f"Offenders={offenders}"
    )

    assert not wrapper_bad, (
        "swe_runner/__init__.py defines resolve_schema_root but does not delegate to swe_schemas.resolve_schema_root() "
        "at call-time. "
        f"Bad={wrapper_bad}"
    )


def test_phase2c_runner_and_planning_surface_bind_to_same_resolver_source() -> None:
    """
    Phase2C(A) contract (strong parity, corrected):
    - Runner and planning/validation surfaces must bind to canonical resolver by importing/using swe_schemas.
    - No local resolve_schema_root definitions are allowed except:
        - src/swe_schemas/** (canonical owner)
        - src/swe_runner/__init__.py (permitted wrapper delegating call-time)
    """
    repo = _repo_root()
    src_root = (repo / "src").resolve()
    assert src_root.exists(), f"missing src root: {src_root}"

    runner_candidates = _collect_candidates(src_root, ["runner"])
    surface_tokens = ["planner", "plan", "planning", "validate", "validator", "validation", "schema", "schemas"]
    surface_candidates = _collect_candidates(src_root, surface_tokens, exclude_tokens=["runner"])

    assert runner_candidates, "No runner candidates found under src/ for Phase2C(A)"
    assert surface_candidates, (
        "No planning/validation surface candidates found under src/ for Phase2C(A). "
        "Expected at least one module path containing one of: planner|plan|planning|validate|validator|validation|schema|schemas"
    )

    runner_bind = _first_binding_module(src_root, runner_candidates)
    surface_bind = _first_binding_module(src_root, surface_candidates)

    assert runner_bind is not None, (
        "Runner parity bind failure: no runner module appears to import/use swe_schemas / resolve_schema_root."
    )
    assert surface_bind is not None, (
        "Surface parity bind failure: no planning/validation surface module appears to import/use swe_schemas / resolve_schema_root."
    )

    _assert_no_local_resolver_clones_except_allowed(src_root)

