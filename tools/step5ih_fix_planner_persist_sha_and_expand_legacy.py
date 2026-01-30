from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path

ROOT = Path(r"C:\Dev\CCP\SWEngineer")
PLANNER = ROOT / "app" / "gui" / "planner.py"
SV = ROOT / "app" / "validation" / "schema_validation.py"

def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def patch_planner() -> None:
    s = PLANNER.read_text(encoding="utf-8")

    # We want: after computing payload["payload_sha256"]=canonical_sha256_for_payload(payload),
    # write it back onto the RunHandoff object so persistence uses canonical sha.
    if "handoff.payload_sha256 = payload[\"payload_sha256\"]" in s:
        print("OK: planner already writes canonical sha back to handoff")
        return

    # Find the exact line where payload_sha256 is set on the dict.
    pat = r'(payload\["payload_sha256"\]\s*=\s*canonical_sha256_for_payload\(payload\)\s*)'
    m = re.search(pat, s)
    if not m:
        raise RuntimeError("FAILURE DETECTED: could not locate canonical_sha256_for_payload assignment in planner.py")

    inject = m.group(1) + "\n        handoff.payload_sha256 = payload[\"payload_sha256\"]\n"
    s2 = s[:m.start(1)] + inject + s[m.end(1):]
    PLANNER.write_text(s2, encoding="utf-8", newline="\n")
    print("PATCHED: planner now persists canonical payload_sha256 into RunHandoff before validation/persist")

def patch_schema_validation() -> None:
    s = SV.read_text(encoding="utf-8")

    # Replace entire _legacy_sha256_variants_for_payload with an expanded, bounded set.
    # We keep it deterministic and strictly limited (no unbounded guessing).
    func_pat = r"def _legacy_sha256_variants_for_payload\([^\)]*\):\n(?:    .*\n)+?(?=\ndef |\nclass |\Z)"
    m = re.search(func_pat, s, flags=re.M)
    if not m:
        raise RuntimeError("FAILURE DETECTED: could not locate _legacy_sha256_variants_for_payload in schema_validation.py")

    repl = r'''def _legacy_sha256_variants_for_payload(payload: Dict[str, Any]) -> List[str]:
    """
    Compatibility window for historical producers + vendor fixtures.

    We only emit a small, bounded set of digests that correspond to known prior encodings:
      - canonical_json(payload_without_sha) (current "legacy base")
      - json.dumps(sort_keys=True, indent=2) + "\\n" (common fixture style)
      - created_utc timezone normalization: "Z" <-> "+00:00" (fixtures vs runtime)
      - separators variants: default vs compact
    """
    # Base payload without its own digest field
    base: Dict[str, Any] = {k: v for k, v in payload.items() if k != "payload_sha256"}

    variants: List[Dict[str, Any]] = [base]

    # created_utc normalization variants (bounded)
    cu = base.get("created_utc")
    if isinstance(cu, str):
        if cu.endswith("Z"):
            v = dict(base)
            v["created_utc"] = cu[:-1] + "+00:00"
            variants.append(v)
        elif cu.endswith("+00:00"):
            v = dict(base)
            v["created_utc"] = cu[:-6] + "Z"
            variants.append(v)

    digests: List[str] = []

    # Helper to hash text with utf-8 exact bytes
    def _hash_text(t: str) -> str:
        return hashlib.sha256(t.encode("utf-8")).hexdigest()

    # Encoding styles (bounded)
    for obj in variants:
        # 1) our historical canonical_json encoding
        try:
            digests.append(sha256_hex(canonical_json(obj)))
        except Exception:
            pass

        # 2) vendor/fixture style: pretty, sorted, newline
        try:
            digests.append(_hash_text(json.dumps(obj, sort_keys=True, indent=2) + "\n"))
        except Exception:
            pass

        # 3) default separators (sorted) + newline (another common fixture habit)
        try:
            digests.append(_hash_text(json.dumps(obj, sort_keys=True) + "\n"))
        except Exception:
            pass

        # 4) compact separators (sorted) + newline
        try:
            digests.append(_hash_text(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"))
        except Exception:
            pass

        # 5) compact separators (sorted) without newline
        try:
            digests.append(_hash_text(json.dumps(obj, sort_keys=True, separators=(",", ":"))))
        except Exception:
            pass

    # de-dup while preserving order
    out: List[str] = []
    seen = set()
    for d in digests:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out
'''

    # Ensure hashlib/json are imported (they already likely are, but we enforce safely)
    if "import hashlib" not in s:
        s = s.replace("import json\n", "import json\nimport hashlib\n", 1)

    s2 = s[:m.start()] + repl + s[m.end():]
    SV.write_text(s2, encoding="utf-8", newline="\n")
    print("PATCHED: expanded legacy sha256 compatibility window (bounded)")

def main() -> int:
    if not PLANNER.exists():
        print(f"FAILURE DETECTED: missing {PLANNER}")
        return 2
    if not SV.exists():
        print(f"FAILURE DETECTED: missing {SV}")
        return 2

    patch_planner()
    patch_schema_validation()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
