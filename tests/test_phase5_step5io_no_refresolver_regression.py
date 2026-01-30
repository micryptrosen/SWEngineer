from __future__ import annotations

import ast
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _uses_refresolver(tree: ast.AST) -> bool:
    """
    Detect real RefResolver usage (imports / attribute access / calls),
    ignoring strings/comments.
    """
    for node in ast.walk(tree):
        # from jsonschema import RefResolver
        if isinstance(node, ast.ImportFrom) and node.module == "jsonschema":
            for alias in node.names:
                if alias.name == "RefResolver":
                    return True

        # import jsonschema (then jsonschema.RefResolver)
        if isinstance(node, ast.Attribute) and node.attr == "RefResolver":
            return True

        # RefResolver(...)
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id == "RefResolver":
                return True
            if isinstance(fn, ast.Attribute) and fn.attr == "RefResolver":
                return True

    return False


def test_no_refresolver_usage_regression() -> None:
    """
    Phase5 invariant:
    SWEngineer must not use jsonschema.RefResolver anywhere (deprecated).
    This test detects actual code usage via AST (not text mentions).
    """
    root = _repo_root()

    scan_dirs = [
        root / "app",
        root / "src",
        root / "tools",
        root / "tests",
    ]

    hits: list[str] = []

    for d in scan_dirs:
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            # Exclude this test file (it necessarily mentions the name).
            if p.resolve() == Path(__file__).resolve():
                continue

            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            try:
                tree = ast.parse(text, filename=str(p))
            except SyntaxError:
                # ignore non-parseable files
                continue

            if _uses_refresolver(tree):
                hits.append(str(p.relative_to(root)))

    assert not hits, "RefResolver usage regression detected in: " + ", ".join(sorted(set(hits)))
