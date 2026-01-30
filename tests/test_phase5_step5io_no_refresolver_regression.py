from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    # tests/ is directly under repo root
    return Path(__file__).resolve().parents[1]


def test_no_refresolver_usage_regression() -> None:
    """
    Phase5 invariant:
    SWEngineer must not *use* jsonschema.RefResolver anywhere (deprecated).
    This test intentionally detects real usage patterns, not mere text mention.
    """
    root = _repo_root()

    # Only scan our code + tools + tests (do not scan vendored schemas/fixtures).
    scan_dirs = [
        root / "app",
        root / "src",
        root / "tools",
        root / "tests",
    ]

    # Real usage patterns we forbid:
    # - from jsonschema import RefResolver
    # - import jsonschema ... RefResolver(...)
    # - jsonschema.RefResolver
    forbidden_snippets = [
        "from jsonschema import RefResolver",
        "import jsonschema\nfrom jsonschema import RefResolver",
        "jsonschema.RefResolver",
        "RefResolver(",
    ]

    hits: list[str] = []

    for d in scan_dirs:
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            # Exclude this file (it necessarily contains the word in comments/docstring).
            if p.resolve() == Path(__file__).resolve():
                continue

            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for snip in forbidden_snippets:
                if snip in text:
                    hits.append(str(p.relative_to(root)))
                    break

    assert not hits, "RefResolver usage regression detected in: " + ", ".join(sorted(set(hits)))
