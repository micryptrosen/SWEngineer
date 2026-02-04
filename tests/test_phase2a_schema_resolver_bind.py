from __future__ import annotations

from pathlib import Path
import sys
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


def _is_schema_module(rel_lower: str) -> bool:
    # Anything that is clearly the schema resolver implementation or bootstrap purge module
    return (
        "swe_schemas" in rel_lower
        or "swe-bootstrap" in rel_lower
        or "swe_bootstrap" in rel_lower
        or "bootstrap" in rel_lower
    )


def test_phase2a_schema_root_is_repo_vendor_bound_and_no_shadow_roots() -> None:
    """
    Phase2A contract (corrected):
    - resolve_schema_root() MUST resolve to <repo>/vendor/swe-schemas
    - At least one execution surface (runner) MUST reference the resolver (bind proof)
    - No shadow roots:
        - no machine-local absolute repo paths embedded under src/
        - no hard-coded vendor/swe-schemas paths under src/ outside the resolver/bootstrap modules
    """
    repo = _repo_root()
    expected = (repo / "vendor" / "swe-schemas").resolve()

    src_root = (repo / "src").resolve()
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    from swe_schemas import resolve_schema_root  # type: ignore

    got = Path(str(resolve_schema_root())).resolve()
    assert got == expected, f"SCHEMA_ROOT drift: got={got} expected={expected}"

    # Scan src for shadow-root regression risks
    bad_abs = str(repo).lower()
    hardcoded_vendor_tokens = ("vendor/swe-schemas", "vendor\\swe-schemas")

    runner_bind_hits: List[str] = []
    hardcoded_hits: List[str] = []
    abs_hits: List[str] = []

    for f in _iter_py_files(src_root):
        rel = f.relative_to(src_root).as_posix()
        rel_lower = rel.lower()
        txt = _read_text(f)
        txt_lower = txt.lower()

        # Absolute machine path references are always forbidden anywhere in src/
        if bad_abs in txt_lower:
            abs_hits.append(rel)

        # Hard-coded vendor path references are forbidden except in schema/bootstrap modules
        if any(tok in txt_lower for tok in hardcoded_vendor_tokens):
            if not _is_schema_module(rel_lower):
                hardcoded_hits.append(rel)

        # Runner bind proof: runner module references resolve_schema_root (or imports it)
        if "runner" in rel_lower and ("resolve_schema_root" in txt or "from swe_schemas" in txt):
            runner_bind_hits.append(rel)

    assert not abs_hits, (
        "Shadow absolute path(s) detected under src/. "
        f"Forbidden references to repo path found in: {abs_hits}"
    )

    assert not hardcoded_hits, (
        "Hard-coded vendor schema path detected outside schema/bootstrap modules under src/. "
        f"Offenders: {hardcoded_hits}"
    )

    assert runner_bind_hits, (
        "No runner module under src/ appears to bind to the schema resolver. "
        "Expected at least one file path containing 'runner' that references resolve_schema_root "
        "or imports swe_schemas."
    )

