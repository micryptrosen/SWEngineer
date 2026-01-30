from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(r"C:\Dev\CCP\SWEngineer")
PL = ROOT / "app" / "gui" / "planner.py"

def main() -> int:
    if not PL.exists():
        print(f"FAILURE DETECTED: missing file: {PL}")
        return 2

    s = PL.read_text(encoding="utf-8")

    # If we already have a correct import, do nothing.
    if re.search(r"from\s+app\.validation\.schema_validation\s+import\s+canonical_sha256_for_payload\b", s):
        print("OK: planner already imports canonical_sha256_for_payload")
        return 0

    # Find an existing import line we can extend safely.
    # Prefer importing from app.validation.schema_validation to avoid circulars.
    insert_line = "from app.validation.schema_validation import canonical_sha256_for_payload\n"

    # Place it after other app.validation imports if present, otherwise after top imports block.
    if "app.validation.schema_validation" in s:
        # If schema_validation is imported in some other form, append next to it.
        # Example patterns:
        #   from app.validation.schema_validation import validate_payload
        #   import app.validation.schema_validation as sv
        m = re.search(r"^(from\s+app\.validation\.schema_validation\s+import\s+.+)$", s, re.M)
        if m:
            line = m.group(1)
            if "canonical_sha256_for_payload" in line:
                print("OK: import line already includes canonical_sha256_for_payload")
                return 0
            # extend the import list
            new_line = line.rstrip() + ", canonical_sha256_for_payload"
            s2 = s[:m.start(1)] + new_line + s[m.end(1):]
            PL.write_text(s2, encoding="utf-8", newline="\n")
            print("PATCHED: extended existing schema_validation import with canonical_sha256_for_payload")
            return 0

    # Otherwise, inject near top: after the last standard import line.
    # We'll insert after the last contiguous import block at file start.
    lines = s.splitlines(True)
    idx = 0
    while idx < len(lines) and (lines[idx].startswith("from ") or lines[idx].startswith("import ") or lines[idx].strip() == ""):
        idx += 1
    lines.insert(idx, insert_line)
    s2 = "".join(lines)
    PL.write_text(s2, encoding="utf-8", newline="\n")
    print("PATCHED: added import canonical_sha256_for_payload to planner")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
