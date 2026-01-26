from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _venv_python(repo: Path) -> Path:
    # Windows venv layout (this repo is Windows-first), but keep a POSIX fallback.
    win = repo / ".venv" / "Scripts" / "python.exe"
    if win.exists():
        return win
    posix = repo / ".venv" / "bin" / "python"
    return posix


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
    """
    repo = _repo_root()
    py = _venv_python(repo)
    assert py.exists(), f"missing venv python at {py}"

    src = repo / "src"
    expected_vendor = (repo / "vendor" / "swe-schemas").resolve()

    code = r"""
import sys
from pathlib import Path

repo = Path(r"%REPO%")
src = repo / "src"
sys.path.insert(0, str(src))

import swe_bootstrap
swe_bootstrap.apply()

import jsonschema  # noqa: F401
import swe_runner  # noqa: F401
import swe_schemas
from app.validation import schema_validation as sv

root1 = Path(swe_schemas.resolve_schema_root()).resolve()
root2 = Path(sv.resolve_schema_root(None)).resolve()
expected = Path(r"%EXPECTED%").resolve()

assert root1 == expected, f"swe_schemas.resolve_schema_root mismatch: {root1} != {expected}"
assert root2 == expected, f"validator resolve_schema_root(None) mismatch: {root2} != {expected}"
assert expected.exists(), f"expected vendor schema root missing: {expected}"

print("ISOLATED_IMPORT_INVARIANT_STEP3J=GREEN")
"""

    code = code.replace("%REPO%", str(repo)).replace("%EXPECTED%", str(expected_vendor))

    r = subprocess.run(
        [str(py), "-I", "-c", code],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        msg = (
            "isolated -I probe failed\n"
            f"exit={r.returncode}\n"
            f"stdout:\n{r.stdout}\n"
            f"stderr:\n{r.stderr}\n"
        )
        raise AssertionError(msg)

    assert "ISOLATED_IMPORT_INVARIANT_STEP3J=GREEN" in r.stdout
