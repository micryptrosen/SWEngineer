from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "app" / "validation" / "schema_validation.py"

def fail(msg: str) -> None:
    raise SystemExit("FAILURE DETECTED: " + msg)

def main() -> None:
    if not FILE.exists():
        fail(f"missing: {FILE}")

    s = FILE.read_text(encoding="utf-8")

    # Ensure hashlib/json available (legacy digest computation uses them)
    if "import hashlib" not in s:
        m = re.search(r"(?m)^(import .+\n)+", s)
        if not m:
            fail("could not find import block anchor for inserting hashlib")
        s = s[:m.end()] + "import hashlib\n" + s[m.end():]

    if re.search(r"(?m)^import json\s*$", s) is None:
        m = re.search(r"(?m)^(import .+\n)+", s)
        if not m:
            fail("could not find import block anchor for inserting json")
        s = s[:m.end()] + "import json\n" + s[m.end():]

    # Insert legacy helper (once) near canonical import
    if "_legacy_sha256_for_payload" not in s:
        anchor = "from app.util.canonical_json import canonical_sha256_for_payload"
        i = s.find(anchor)
        if i < 0:
            fail("expected canonical_sha256_for_payload import not found")
        # place helper shortly after the import line
        j = s.find("\n", i)
        insert_at = j + 1

        helper = r'''
def _legacy_sha256_for_payload(payload: Dict[str, Any]) -> str:
    """
    Compatibility digest for pre-Step5IE producers and vendor fixtures.
    Canonical-ish but legacy: compact separators, ensure_ascii=True, no trailing newline.
    """
    p = dict(payload)
    p.pop("payload_sha256", None)
    txt = json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()

'''
        s = s[:insert_at] + helper + s[insert_at:]

    # Replace _enforce_payload_sha256(...) block
    m = re.search(r"(?ms)^def _enforce_payload_sha256\(.*?\) -> None:\n.*?\n(?=^def |\Z)", s)
    if not m:
        fail("could not locate _enforce_payload_sha256(...) block")

    new_def = r'''def _enforce_payload_sha256(payload: Dict[str, Any], *, strict: bool = True) -> None:
    """
    Phase 2E invariant + compatibility window:
      - payload_sha256 must exist
      - must be 64 lowercase hex
      - when strict=True: must verify against either:
          (a) Step5IE canonical digest (preferred)
          (b) legacy digest used by pre-Step5IE producers + vendor fixtures
    """
    got = payload.get("payload_sha256")
    if not isinstance(got, str):
        raise SchemaValidationError("payload_sha256 is required")
    if not _SHA256_RE.match(got):
        raise SchemaValidationError("payload_sha256 must be 64 lowercase hex")

    if strict:
        want_new = canonical_sha256_for_payload(payload)
        if got == want_new:
            return
        want_legacy = _legacy_sha256_for_payload(payload)
        if got == want_legacy:
            return
        raise SchemaValidationError("payload_sha256 does not match canonical or legacy payload digest")
'''
    s = s[:m.start()] + new_def + "\n\n" + s[m.end():]

    FILE.write_text(s, encoding="utf-8", newline="\n")
    print("STEP5IF_SHA_COMPAT_PATCH=OK")

if __name__ == "__main__":
    main()
