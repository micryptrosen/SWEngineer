from __future__ import annotations

import sys
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _expected_schema_root(root: Path) -> Path:
    return (root / "vendor" / "swe-schemas").resolve()


def _assert_uses_canonical_schema_plumbing(mod, swe_schemas_mod):
    """
    Canonical binding is satisfied if EITHER:
      A) module binds canonical swe_schemas module object (preferred), OR
      B) module exposes resolve_schema_root identical to swe_schemas.resolve_schema_root
    """
    d = getattr(mod, "__dict__", {})
    uses_module = ("swe_schemas" in d) and (d["swe_schemas"] is swe_schemas_mod)
    uses_func = ("resolve_schema_root" in d) and (d["resolve_schema_root"] is swe_schemas_mod.resolve_schema_root)
    if not (uses_module or uses_func):
        keys = sorted([k for k in d.keys() if k in ("swe_schemas", "resolve_schema_root")])
        raise AssertionError(
            "schema-root plumbing is not canonical for module="
            + getattr(mod, "__name__", "<unknown>")
            + "\nExpected either mod.swe_schemas is swe_schemas OR mod.resolve_schema_root is swe_schemas.resolve_schema_root"
            + "\nFound relevant keys: "
            + (", ".join(keys) if keys else "(none)")
        )


def test_runner_and_validator_use_same_canonical_schema_root_plumbing():
    root = _repo_root()

    import swe_bootstrap
    swe_bootstrap.apply()

    import swe_schemas
    expected = _expected_schema_root(root)
    got = Path(swe_schemas.resolve_schema_root()).resolve()
    assert got == expected, f"canonical schema root mismatch: got={got} expected={expected}"

    import swe_runner
    import app.validation.schema_validation as schema_validation

    _assert_uses_canonical_schema_plumbing(swe_runner, swe_schemas)
    _assert_uses_canonical_schema_plumbing(schema_validation, swe_schemas)


def test_isolated_python_imports_runner_and_validator_and_they_bind_to_canonical_plumbing():
    root = _repo_root()
    expected = _expected_schema_root(root)

    code = r"""
import sys
from pathlib import Path

root = Path(r"{ROOT}").resolve()
src = (root / "src").resolve()
sys.path.insert(0, str(src))

import swe_bootstrap
swe_bootstrap.apply()

import swe_schemas
got = Path(swe_schemas.resolve_schema_root()).resolve()
print("CANON=" + str(got))

import swe_runner
import app.validation.schema_validation as schema_validation

ok_runner = ("swe_schemas" in swe_runner.__dict__ and swe_runner.__dict__["swe_schemas"] is swe_schemas) or \
            ("resolve_schema_root" in swe_runner.__dict__ and swe_runner.__dict__["resolve_schema_root"] is swe_schemas.resolve_schema_root)

ok_validator = ("swe_schemas" in schema_validation.__dict__ and schema_validation.__dict__["swe_schemas"] is swe_schemas) or \
               ("resolve_schema_root" in schema_validation.__dict__ and schema_validation.__dict__["resolve_schema_root"] is swe_schemas.resolve_schema_root)

print("RUNNER_CANON=" + ("YES" if ok_runner else "NO"))
print("VALIDATOR_CANON=" + ("YES" if ok_validator else "NO"))
""".replace("{ROOT}", str(root))

    proc = subprocess.run([sys.executable, "-I", "-c", code], text=True, capture_output=True)
    if proc.returncode != 0:
        raise AssertionError("isolated subprocess failed:\nSTDOUT:\n"
                             + (proc.stdout or "")
                             + "\nSTDERR:\n"
                             + (proc.stderr or ""))

    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    canon = None
    runner_ok = None
    validator_ok = None
    for ln in lines:
        if ln.startswith("CANON="):
            canon = Path(ln.split("=", 1)[1]).resolve()
        if ln.startswith("RUNNER_CANON="):
            runner_ok = (ln.split("=", 1)[1].strip() == "YES")
        if ln.startswith("VALIDATOR_CANON="):
            validator_ok = (ln.split("=", 1)[1].strip() == "YES")

    assert canon == expected, f"isolation canon root mismatch: got={canon} expected={expected}"
    assert runner_ok is True, "runner is not bound to canonical swe_schemas plumbing under -I"
    assert validator_ok is True, "validator is not bound to canonical swe_schemas plumbing under -I"
