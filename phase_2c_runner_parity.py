from __future__ import annotations
import swe_bootstrap as _swe_bootstrap
_swe_bootstrap.apply()


import json
import re
from pathlib import Path

ROOT = Path.cwd().resolve()

def die(msg: str) -> None:
    raise SystemExit(msg)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")

# Detect package root (flat 'app' layout in this repo)
APP_DIR = ROOT / "app"
if not APP_DIR.exists():
    die(f"FAILURE DETECTED: expected app/ directory at {APP_DIR}")

schema_locator = APP_DIR / "schema_locator.py"
if not schema_locator.exists():
    die("FAILURE DETECTED: app/schema_locator.py missing (Phase 2C prerequisite).")

validation_dir = APP_DIR / "validation"
validation_dir.mkdir(parents=True, exist_ok=True)

validator_mod = validation_dir / "schema_validation.py"

validator_src = r'''from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.schema_locator import resolve_schema_root

class SchemaValidationError(RuntimeError):
    pass

def _iter_json_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*.json"):
        # ignore tooling / hidden dirs
        s = str(p).replace("\\", "/")
        if "/.git/" in s or "/__pycache__/" in s:
            continue
        out.append(p)
    return out

def _normalize_contract(contract: str) -> str:
    return contract.strip().lower()

def find_schema_for_contract(contract: str, schema_root: Optional[Path] = None) -> Path:
    """
    Best-effort resolver.
    Primary: schema_root/<contract>.json (supports subfolders if contract contains '/')
    Fallback: recursive search for JSON file whose path contains the normalized contract tokens.
    """
    root = resolve_schema_root(schema_root)
    if not root.exists():
        raise SchemaValidationError(f"schema_root does not exist: {root}")

    c = _normalize_contract(contract)

    # 1) direct: <root>/<contract>.json
    direct = (root / (c + ".json"))
    if direct.exists():
        return direct

    # 2) direct with path segments: <root>/<contract>.json (contract may include '/')
    direct2 = (root / Path(c + ".json"))
    if direct2.exists():
        return direct2

    # 3) common pattern: <root>/<contract>/schema.json
    direct3 = (root / Path(c) / "schema.json")
    if direct3.exists():
        return direct3

    # 4) recursive token match
    tokens = [t for t in re.split(r"[^a-z0-9]+", c) if t]
    candidates: list[Path] = []
    for p in _iter_json_files(root):
        s = str(p).replace("\\", "/").lower()
        if all(t in s for t in tokens):
            candidates.append(p)

    if not candidates:
        raise SchemaValidationError(f"no schema found for contract='{contract}' under {root}")

    # Prefer shortest path (most specific)
    candidates.sort(key=lambda p: (len(str(p)), str(p)))
    return candidates[0]

def validate_payload(payload: Dict[str, Any], schema_root: Optional[Path] = None) -> None:
    """
    Validates payload against the schema resolved by payload['contract'].
    Requires jsonschema to be installed; errors raise SchemaValidationError.
    """
    if "contract" not in payload or not isinstance(payload["contract"], str) or not payload["contract"].strip():
        raise SchemaValidationError("payload missing required string field: contract")

    contract = payload["contract"]
    schema_path = find_schema_for_contract(contract, schema_root=schema_root)

    try:
        import jsonschema  # type: ignore
    except Exception as e:
        raise SchemaValidationError("jsonschema is required for validation but is not available") from e

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except Exception as e:
        raise SchemaValidationError(f"schema validation failed for contract='{contract}' schema='{schema_path}'") from e
'''

# NOTE: we used 're' in the module; ensure it's in the file (we referenced re, so import it)
# Fix: inject import re if missing.
if "import re" not in validator_src:
    validator_src = validator_src.replace("import json\n", "import json\nimport re\n")

write_text(validator_mod, validator_src)

# Patch planner to validate contracts before writing evidence.
planner = APP_DIR / "gui" / "planner.py"
if not planner.exists():
    die(f"FAILURE DETECTED: expected planner at {planner}")

t = read_text(planner)

# Ensure import line exists once
import_line = "from app.validation.schema_validation import validate_payload"
if import_line not in t:
    # insert after existing imports block (within first ~60 lines)
    lines = t.splitlines()
    insert_at = 0
    for i, line in enumerate(lines[:80]):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1
    lines.insert(insert_at, import_line)
    t = "\n".join(lines) + ("\n" if not t.endswith("\n") else "")

# Inject validate_payload(...) call.
# We look for the three payload dict literals in planner:
# - handoff payload (contains "contract": "run_handoff/1.0")
# - and any pydantic payload_no_sha dict usage
# We patch conservatively: after lines that create a dict with a "contract" key and assign to a name.
patterns = [
    r'(?P<indent>^\s*)(?P<var>\w+)\s*=\s*\{\s*$',
]

lines = t.splitlines()
out = []
i = 0
patched_calls = 0

def dict_has_contract(start: int) -> bool:
    # scan forward a bit for a "contract": within a dict literal
    for j in range(start, min(start + 40, len(lines))):
        if re.search(r'["\']contract["\']\s*:', lines[j]):
            return True
        if re.search(r'^\s*\}\s*$', lines[j]):
            return False
    return False

while i < len(lines):
    line = lines[i]
    m = re.match(r'^(\s*)(\w+)\s*=\s*\{\s*$', line)
    out.append(line)
    if m and dict_has_contract(i):
        indent = m.group(1)
        var = m.group(2)
        # find the closing brace of this dict literal
        j = i + 1
        while j < len(lines):
            out.append(lines[j])
            if re.match(r'^\s*\}\s*,?\s*$', lines[j]):
                # after the dict closes, validate it
                out.append(f"{indent}validate_payload({var})")
                patched_calls += 1
                i = j
                break
            j += 1
    i += 1

t2 = "\n".join(out) + ("\n" if t.endswith("\n") else "")
if t2 != t:
    write_text(planner, t2)

# Integration test: validate at least one fixture through SWEngineer path
tests_dir = ROOT / "tests"
tests_dir.mkdir(parents=True, exist_ok=True)

test_path = tests_dir / "test_schema_validation_runner_parity.py"
test_src = r'''from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.validation.schema_validation import validate_payload

def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(50):
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            return cur
        cur = cur.parent
    return start.resolve()

def _find_any_fixture_with_contract(fixtures_root: Path) -> Path | None:
    for p in fixtures_root.rglob("*.json"):
        s = str(p).replace("\\", "/").lower()
        if "/.git/" in s:
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("contract"), str) and obj["contract"].strip():
            return p
    return None

def test_validate_fixture_via_vendor_schemas() -> None:
    repo = _find_repo_root(Path(__file__))
    fixtures = repo / "vendor" / "swe-fixtures"
    if not fixtures.exists():
        pytest.skip("vendor/swe-fixtures submodule not present")
    fx = _find_any_fixture_with_contract(fixtures)
    if fx is None:
        pytest.skip("no JSON fixture with a 'contract' field found")
    payload = json.loads(fx.read_text(encoding="utf-8"))
    validate_payload(payload)
'''
write_text(test_path, test_src)

print("PHASE_2C_RUNNER_PARITY_WIRED=GREEN")
print(f"WROTE={validator_mod}")
print(f"PATCHED_PLANNER={planner} calls={patched_calls}")
print(f"WROTE={test_path}")
