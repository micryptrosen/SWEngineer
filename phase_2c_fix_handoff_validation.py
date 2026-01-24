from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd().resolve()
PLANNER = ROOT / "app" / "gui" / "planner.py"
if not PLANNER.exists():
    raise SystemExit(f"FAILURE DETECTED: missing {PLANNER}")

txt = PLANNER.read_text(encoding="utf-8")

# 1) Remove/disable the premature validation call that breaks schema (payload_no_sha lacks payload_sha256).
txt2 = txt.replace("validate_payload(payload_no_sha)", "# validate_payload(payload_no_sha)  # deferred: requires payload_sha256")
changed = (txt2 != txt)
txt = txt2

# 2) Ensure we validate the final payload AFTER payload_sha256 is set.
# We look for a line assigning payload_sha256, then insert validate_payload(payload) once after it.
lines = txt.splitlines()
out = []
inserted = False
for i, line in enumerate(lines):
    out.append(line)
    if not inserted:
        # Common patterns we accept:
        # payload["payload_sha256"] = ...
        # payload_sha256 = ...
        # payload.update({"payload_sha256": ...})
        if re.search(r'payload\[\s*["\']payload_sha256["\']\s*\]\s*=', line):
            out.append("    validate_payload(payload)")
            inserted = True
        elif re.search(r'payload\.update\(\s*\{[^}]*["\']payload_sha256["\']\s*:', line):
            out.append("    validate_payload(payload)")
            inserted = True

txt3 = "\n".join(out) + ("\n" if txt.endswith("\n") else "")
if txt3 != txt:
    changed = True
    txt = txt3

if not inserted:
    raise SystemExit(
        "FAILURE DETECTED: could not find where payload_sha256 is set in planner.py to insert validate_payload(payload). "
        "We need to patch with a more specific anchor."
    )

if not changed:
    print("PLANNER_PATCH_NOOP=OK (already patched)")
else:
    PLANNER.write_text(txt, encoding="utf-8", newline="\n")
    print("PLANNER_PATCHED=GREEN")
