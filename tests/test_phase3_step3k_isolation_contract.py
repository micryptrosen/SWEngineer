from __future__ import annotations

import sys
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_schema_root_is_vendor_swe_schemas_absolute():
    """
    Contract: schema root resolves to <repo>/vendor/swe-schemas (no fallback).
    """
    root = _repo_root()

    import swe_bootstrap
    swe_bootstrap.apply()

    import swe_schemas
    schema_root = Path(swe_schemas.resolve_schema_root()).resolve()

    expected = (root / "vendor" / "swe-schemas").resolve()
    assert schema_root == expected, f"schema_root mismatch: got={schema_root} expected={expected}"
    assert expected.is_dir(), f"expected schema root dir missing: {expected}"


def test_isolated_python_can_import_bootstrap_from_src_and_resolve_vendor_schema_root():
    """
    Contract: under `python -I`, we can still:
      - make modules discoverable via <repo>/src (src-layout reality),
      - apply bootstrap,
      - resolve schema root to <repo>/vendor/swe-schemas (no fallback).

    This matches the intended runner/bootstrap contract more closely than adding only repo root.
    """
    root = _repo_root()
    src = (root / "src").resolve()
    expected = (root / "vendor" / "swe-schemas").resolve()

    code = r"""
import sys
from pathlib import Path

root = Path(r"{ROOT}").resolve()
src = (root / "src").resolve()

# src-layout discoverability in isolated mode
sys.path.insert(0, str(src))

import swe_bootstrap
swe_bootstrap.apply()

import swe_schemas
p = Path(swe_schemas.resolve_schema_root()).resolve()
print(str(p))
""".replace("{ROOT}", str(root))

    proc = subprocess.run([sys.executable, "-I", "-c", code], text=True, capture_output=True)
    if proc.returncode != 0:
        raise AssertionError("isolated subprocess failed:\nSTDOUT:\n"
                             + (proc.stdout or "")
                             + "\nSTDERR:\n"
                             + (proc.stderr or ""))

    got = Path(proc.stdout.strip()).resolve()
    assert got == expected, f"isolation contract failed: got={got} expected={expected}"
    assert src.is_dir(), f"expected src dir missing: {src}"
