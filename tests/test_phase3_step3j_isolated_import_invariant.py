from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _python_for_isolation(repo: Path) -> Path:
    """
    Isolation invariant should NOT require a pre-provisioned venv in a clean clone.
    Prefer .venv if present; otherwise fall back to the current interpreter.
    Windows: .venv\\Scripts\\python.exe
    POSIX:   .venv/bin/python
    """
    win = repo / ".venv" / "Scripts" / "python.exe"
    posix = repo / ".venv" / "bin" / "python"
    if win.exists():
        return win
    if posix.exists():
        return posix
    return Path(sys.executable)


def test_isolated_import_invariant_I_bootstrap_validator_jsonschema() -> None:
    """
    Phase 3 / Step 3J invariant (permanent):
    In a fully isolated interpreter (-I), with ONLY repo/src injected:
      - import swe_bootstrap + apply()
      - import swe_schemas + resolve_schema_root()
      - import app.validation.schema_validation (validator)
      - import jsonschema
      - import swe_runner
    Must succeed deterministically.

    Note: In a clean clone proof, a repo-local venv may not exist; we allow sys.executable.
    """
    repo = _repo_root()
    py = _python_for_isolation(repo)
    assert py.exists(), f"missing python interpreter at {py}"

    code = r"""
import os
import sys
from pathlib import Path

root = Path(r"{ROOT}").resolve()
src = (root / "src").resolve()

# Ensure repo-under-test src wins in isolated mode
sys.path.insert(0, str(src))

import swe_bootstrap
swe_bootstrap.apply()

import swe_schemas
p = Path(swe_schemas.resolve_schema_root()).resolve()
print("SCHEMA_ROOT=" + str(p))

import app.validation.schema_validation as schema_validation
import jsonschema
import swe_runner

print("OK=YES")
""".replace("{ROOT}", str(repo))

    proc = subprocess.run([str(py), "-I", "-c", code], text=True, capture_output=True)
    if proc.returncode != 0:
        raise AssertionError(
            "isolated subprocess failed:\nSTDOUT:\n"
            + (proc.stdout or "")
            + "\nSTDERR:\n"
            + (proc.stderr or "")
        )

    out = (proc.stdout or "").strip()
    assert "OK=YES" in out
