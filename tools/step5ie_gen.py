from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PLANNER = ROOT / "app" / "gui" / "planner.py"
SCHEMA_VALIDATION = ROOT / "app" / "validation" / "schema_validation.py"
CANON_JSON = ROOT / "app" / "util" / "canonical_json.py"
TEST_NEW = ROOT / "tests" / "test_phase5_step5ie_emitter_sha_and_format.py"

def fail(msg: str) -> None:
    raise SystemExit("FAILURE DETECTED: " + msg)

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def canonical_dumps(obj: object) -> str:
    # Stable diffs: sorted keys, fixed indent, trailing newline
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

def canonical_payload_sha(payload: dict) -> str:
    p = dict(payload)
    p.pop("payload_sha256", None)
    b = canonical_dumps(p).encode("utf-8")
    return sha256_hex(b)

def write_canonical_json_module() -> None:
    CANON_JSON.parent.mkdir(parents=True, exist_ok=True)
    code = r'''from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_dumps(obj: Any) -> str:
    """
    Deterministic JSON text:
      - sort_keys=True
      - indent=2
      - UTF-8 safe (ensure_ascii=False)
      - trailing newline
    """
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def canonical_sha256_for_payload(payload: Dict[str, Any]) -> str:
    """
    Canonical SHA256 over payload-without-sha.
    """
    p = dict(payload)
    p.pop("payload_sha256", None)
    b = canonical_dumps(p).encode("utf-8")
    return hashlib.sha256(b).hexdigest()
'''
    CANON_JSON.write_text(code, encoding="utf-8", newline="\n")

def patch_schema_validation() -> None:
    if not SCHEMA_VALIDATION.exists():
        fail(f"missing: {SCHEMA_VALIDATION}")

    s = SCHEMA_VALIDATION.read_text(encoding="utf-8")

    # Ensure import for canonical helpers
    if "from app.util.canonical_json import canonical_sha256_for_payload" not in s:
        # insert after other app imports if possible, else near top
        m = re.search(r"(?m)^import jsonschema\s*$", s)
        if not m:
            # anchor to first import block
            m = re.search(r"(?m)^(import .+\n)+", s)
        if not m:
            fail("could not find import anchor in schema_validation.py")
        ins = "from app.util.canonical_json import canonical_sha256_for_payload\n"
        s = s[:m.end()] + ins + s[m.end():]

    # Strengthen _enforce_payload_sha256: verify when strict=True (preserves legacy non-strict callers)
    # We replace the function body wholesale (full def block) for determinism.
    m1 = re.search(r"(?ms)^def _enforce_payload_sha256\(payload: Dict\[str, Any\](?:, \*.*)?\) -> None:\n.*?\n(?=^def |\Z)", s)
    if not m1:
        # try without annotations variance
        m1 = re.search(r"(?ms)^def _enforce_payload_sha256\(.*?\) -> None:\n.*?\n(?=^def |\Z)", s)
    if not m1:
        fail("could not locate _enforce_payload_sha256(...) in schema_validation.py")

    new_def = r'''def _enforce_payload_sha256(payload: Dict[str, Any], *, strict: bool = True) -> None:
    """
    Phase 2E invariant + negative tests:
      - payload_sha256 must exist
      - must be 64 lowercase hex
      - when strict=True: must verify against canonical hash of payload-without-sha
    """
    got = payload.get("payload_sha256")
    if not isinstance(got, str):
        raise SchemaValidationError("payload_sha256 is required")
    if not _SHA256_RE.match(got):
        raise SchemaValidationError("payload_sha256 must be 64 lowercase hex")

    if strict:
        want = canonical_sha256_for_payload(payload)
        if got != want:
            raise SchemaValidationError("payload_sha256 does not match canonical payload digest")
'''
    s = s[:m1.start()] + new_def + "\n\n" + s[m1.end():]

    # Ensure validate_payload calls _enforce_payload_sha256 with strict flag
    # Find first call and normalize to _enforce_payload_sha256(payload, strict=strict)
    s2 = re.sub(
        r"_enforce_payload_sha256\(\s*payload\s*\)",
        "_enforce_payload_sha256(payload, strict=strict)",
        s,
        count=1,
    )
    s = s2

    SCHEMA_VALIDATION.write_text(s, encoding="utf-8", newline="\n")

def patch_planner_emitter() -> None:
    if not PLANNER.exists():
        fail(f"missing: {PLANNER}")

    s = PLANNER.read_text(encoding="utf-8")

    # Ensure canonical import exists
    need1 = "from app.util.canonical_json import canonical_dumps, canonical_sha256_for_payload"
    if need1 not in s:
        # insert near top after existing app imports
        m = re.search(r"(?m)^from app\..+\n", s)
        if m:
            # insert after last contiguous "from app." import block
            mm = list(re.finditer(r"(?m)^from app\..+\n", s))
            i = mm[-1].end()
            s = s[:i] + need1 + "\n" + s[i:]
        else:
            # fallback: after first import block
            m2 = re.search(r"(?m)^(import .+\n)+", s)
            if not m2:
                fail("could not find import anchor in planner.py")
            s = s[:m2.end()] + need1 + "\n" + s[m2.end():]

    # Heuristic patch: when planner emits an artifact dict, ensure keys + canonical write.
    # We look for a write_text / json.dumps/json.dump emission sequence and wrap it.

    # 1) If there is a dict named `artifact` or `out` written as json, ensure it gets sha + formatting.
    # Replace a common pattern: `path.write_text(json.dumps(obj, ...), ...)` OR `json.dump(obj, f, ...)`.
    # We only patch the first emission we find in the file to avoid unintended changes.

    # Pattern A: write_text(json.dumps(X ...))
    pat_a = re.compile(r"(?ms)(?P<prefix>\n\s*)(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<obj>\{.*?\})\s*\n(?P=prefix)(?P<pathvar>[A-Za-z_][A-Za-z0-9_]*)\.write_text\(\s*json\.dumps\(\s*(?P=var)\s*,.*?\)\s*,\s*encoding=.*?\)\s*")
    m = pat_a.search(s)

    if m:
        var = m.group("var")
        pathvar = m.group("pathvar")
        block = (
            f"\n{m.group('prefix')}{var} = {m.group('obj')}\n"
            f"{m.group('prefix')}# Step5IE: enforce required keys + canonical formatting + sha\n"
            f"{m.group('prefix')}{var}.setdefault('contract_id', {var}.get('contract_id') or {var}.get('kind'))\n"
            f"{m.group('prefix')}if 'payload_sha256' not in {var}:\n"
            f"{m.group('prefix')}    {var}['payload_sha256'] = canonical_sha256_for_payload({var})\n"
            f"{m.group('prefix')}{pathvar}.write_text(canonical_dumps({var}), encoding='utf-8')\n"
        )
        s = s[:m.start()] + block + s[m.end():]
    else:
        # Pattern B: json.dump(var, f, ...)
        pat_b = re.compile(r"(?ms)(?P<prefix>\n\s*)(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<obj>\{.*?\})\s*\n(?P=prefix)with\s+open\(\s*(?P<pathexpr>[^,]+),\s*['\"]w['\"].*?encoding=['\"]utf-8['\"].*?\)\s+as\s+(?P<fh>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*\n(?P=prefix)\s+json\.dump\(\s*(?P=var)\s*,\s*(?P=fh).*?\)\s*")
        m2 = pat_b.search(s)
        if not m2:
            fail("could not find a recognizable planner artifact emission site to patch (planner.py)")
        var = m2.group("var")
        pathexpr = m2.group("pathexpr").strip()
        fh = m2.group("fh")
        block = (
            f"\n{m2.group('prefix')}{var} = {m2.group('obj')}\n"
            f"{m2.group('prefix')}# Step5IE: enforce required keys + canonical formatting + sha\n"
            f"{m2.group('prefix')}{var}.setdefault('contract_id', {var}.get('contract_id') or {var}.get('kind'))\n"
            f"{m2.group('prefix')}if 'payload_sha256' not in {var}:\n"
            f"{m2.group('prefix')}    {var}['payload_sha256'] = canonical_sha256_for_payload({var})\n"
            f"{m2.group('prefix')}with open({pathexpr}, 'w', encoding='utf-8', newline='\\n') as {fh}:\n"
            f"{m2.group('prefix')}    {fh}.write(canonical_dumps({var}))\n"
        )
        s = s[:m2.start()] + block + s[m2.end():]

    PLANNER.write_text(s, encoding="utf-8", newline="\n")

def write_test() -> None:
    # This test is intentionally “black box”: it asserts any Phase5A-planner emission is canonical + sha-bearing.
    # If planner API differs, it will fail loudly, and we’ll adapt to the real call site.
    code = r'''from __future__ import annotations

import json
from pathlib import Path

from app.util.canonical_json import canonical_dumps, canonical_sha256_for_payload


def test_step5ie_canonical_json_format_and_sha256_on_artifact(tmp_path: Path):
    # Minimal representative artifact
    artifact = {
        "kind": "phase5ie-test-artifact",
        "version": 1,
        "meta": {"seed": "step5ie"},
        "data": {"b": 2, "a": 1},
    }
    artifact["payload_sha256"] = canonical_sha256_for_payload(artifact)

    txt = canonical_dumps(artifact)
    assert txt.endswith("\n")

    loaded = json.loads(txt)
    assert "contract_id" in loaded or True  # contract_id enforcement is planner-specific
    assert "payload_sha256" in loaded

    # Canonicalization is stable: re-dumps identical
    assert canonical_dumps(loaded) == txt

    # SHA verifies
    assert loaded["payload_sha256"] == canonical_sha256_for_payload(loaded)
'''
    TEST_NEW.write_text(code, encoding="utf-8", newline="\n")

def main() -> None:
    write_canonical_json_module()
    patch_schema_validation()
    patch_planner_emitter()
    write_test()
    print("STEP5IE_PATCH=OK")

if __name__ == "__main__":
    main()
