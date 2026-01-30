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

    # Must exist from Step5IF
    if "_legacy_sha256_for_payload" not in s:
        fail("expected _legacy_sha256_for_payload not found (Step5IF missing?)")

    # Replace only the helper body with multi-variant legacy acceptance
    m = re.search(r"(?ms)^def _legacy_sha256_for_payload\(payload: Dict\[str, Any\]\) -> str:\n.*?\n(?=^def |\Z)", s)
    if not m:
        fail("could not locate _legacy_sha256_for_payload(...) block")

    new_block = r'''def _legacy_sha256_for_payload(payload: Dict[str, Any]) -> str:
    """
    Compatibility digests for pre-Step5IE producers and vendor fixtures.

    We accept a small, explicit set of legacy canonicalization styles:
      A) compact JSON: separators=(',', ':'), ensure_ascii=True
      B) pretty JSON: indent=2, sort_keys=True, ensure_ascii=False, with trailing '\\n'
      C) pretty JSON: indent=2, sort_keys=True, ensure_ascii=False, no trailing newline

    We return the FIRST variant's digest (A) for callers that want "a legacy digest",
    but _enforce_payload_sha256() may compare against multiple variants by calling
    _legacy_sha256_variants_for_payload().
    """
    return _legacy_sha256_variants_for_payload(payload)[0]

def _legacy_sha256_variants_for_payload(payload: Dict[str, Any]) -> List[str]:
    p = dict(payload)
    p.pop("payload_sha256", None)

    variants: List[bytes] = []

    # A) compact
    txt_a = json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    variants.append(txt_a.encode("utf-8"))

    # B) pretty + newline (most common fixture style)
    txt_b = json.dumps(p, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    variants.append(txt_b.encode("utf-8"))

    # C) pretty (no newline)
    txt_c = json.dumps(p, sort_keys=True, indent=2, ensure_ascii=False)
    variants.append(txt_c.encode("utf-8"))

    out: List[str] = []
    for b in variants:
        out.append(hashlib.sha256(b).hexdigest())
    return out
'''

    s2 = s[:m.start()] + new_block + "\n\n" + s[m.end():]

    # Patch _enforce_payload_sha256 to compare against ALL legacy variants
    m2 = re.search(r"(?ms)^def _enforce_payload_sha256\(.*?\) -> None:\n.*?\n(?=^def |\Z)", s2)
    if not m2:
        fail("could not locate _enforce_payload_sha256(...) block")

    block2 = m2.group(0)
    if "_legacy_sha256_variants_for_payload" not in block2:
        # Replace the single-legacy check with a variants loop
        block2_new = re.sub(
            r"(?ms)\s*want_legacy\s*=\s*_legacy_sha256_for_payload\(payload\)\s*\n\s*if got == want_legacy:\s*\n\s*return\s*\n\s*raise SchemaValidationError\([^)]+\)\s*",
            "\n        for want_legacy in _legacy_sha256_variants_for_payload(payload):\n"
            "            if got == want_legacy:\n"
            "                return\n"
            "        raise SchemaValidationError(\"payload_sha256 does not match canonical or any known legacy payload digest\")\n",
            block2,
        )
        if block2_new == block2:
            fail("could not patch legacy comparison in _enforce_payload_sha256")
        s2 = s2[:m2.start()] + block2_new + "\n\n" + s2[m2.end():]

    FILE.write_text(s2, encoding="utf-8", newline="\n")
    print("STEP5IG_VENDOR_FIXTURE_SHA_COMPAT=OK")

if __name__ == "__main__":
    main()
