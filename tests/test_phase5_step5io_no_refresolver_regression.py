from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    # tests/ is directly under repo root
    return Path(__file__).resolve().parents[1]


def test_no_refresolver_regression() -> None:
    """
    Phase5/Step5IO invariant:
    SWEngineer must not use jsonschema.RefResolver anywhere (deprecated; replaced by referencing.Registry).
    This prevents silent reintroduction of DeprecationWarnings and keeps the resolver modernization intact.
    """
    root = _repo_root()

    # Only scan our code + tools + tests (do not scan vendored schemas/fixtures).
    scan_dirs = [
        root / "app",
        root / "src",
        root / "tools",
        root / "tests",
    ]

    hits = []
    for d in scan_dirs:
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "RefResolver" in text:
                hits.append(str(p.relative_to(root)))

    assert not hits, "RefResolver regression detected in: " + ", ".join(hits)
