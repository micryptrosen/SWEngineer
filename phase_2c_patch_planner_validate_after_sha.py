from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd().resolve()
P = ROOT / "app" / "gui" / "planner.py"
if not P.exists():
    raise SystemExit(f"FAILURE DETECTED: missing {P}")

lines = P.read_text(encoding="utf-8").splitlines()

# 1) Replace exact premature validate call
removed = 0
out = []
for line in lines:
    if line.strip() == "validate_payload(payload_no_sha)":
        out.append(line.replace("validate_payload(payload_no_sha)", "# validate_payload(payload_no_sha)  # deferred: schema requires payload_sha256"))
        removed += 1
    else:
        out.append(line)

if removed != 1:
    raise SystemExit(f"FAILURE DETECTED: expected exactly 1 'validate_payload(payload_no_sha)' line; found {removed}")

# 2) Insert validate after handoff construction, before payload = json.dumps(...)
inserted = 0
final = []
for i, line in enumerate(out):
    final.append(line)
    if line.strip() == "payload_sha256=sha,":
        # lookahead for closing paren of RunHandoff(...) in next few lines
        continue
    if line.strip() == ")" and i >= 1 and "handoff = RunHandoff(" in out[max(0, i-30):i]:
        # Ensure we only insert once, and only in the handoff constructor close
        # Insert on next line (same indent level as 'handoff = ...' block, which is 4 spaces in this file)
        if inserted == 0:
            final.append("")
            final.append("    # Validate final handoff payload (includes payload_sha256)")
            final.append("    validate_payload(asdict(handoff))")
            inserted += 1

if inserted != 1:
    raise SystemExit(f"FAILURE DETECTED: expected to insert validate after handoff construction exactly once; inserted={inserted}")

P.write_text("\n".join(final) + "\n", encoding="utf-8", newline="\n")
print("PLANNER_HANDOFF_VALIDATION_PATCHED=GREEN")
