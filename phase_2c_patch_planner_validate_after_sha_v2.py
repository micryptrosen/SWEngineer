from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd().resolve()
P = ROOT / "app" / "gui" / "planner.py"
txt = P.read_text(encoding="utf-8").splitlines()

removed = 0
inserted = 0
out = []

for line in txt:
    if "validate_payload(payload_no_sha)" in line and not line.strip().startswith("#"):
        out.append(line.replace("validate_payload(payload_no_sha)", "# validate_payload(payload_no_sha)  # deferred: schema requires payload_sha256"))
        removed += 1
    else:
        out.append(line)

final = []
for i, line in enumerate(out):
    final.append(line)
    if "payload_sha256=sha," in line:
        # insert validate right after this line if not already present nearby
        window = "\n".join(out[i:min(len(out), i+6)])
        if "validate_payload(asdict(handoff))" not in window and "validate_payload(payload)" not in window:
            indent = line[:len(line) - len(line.lstrip(" "))]
            final.append(indent + "validate_payload(asdict(handoff))")
            inserted += 1

P.write_text("\n".join(final) + "\n", encoding="utf-8", newline="\n")

print(f"PLANNER_PATCHED=GREEN removed={removed} inserted={inserted}")
if removed != 1:
    raise SystemExit(f"FAILURE DETECTED: expected removed=1 for validate_payload(payload_no_sha); got {removed}")
if inserted != 1:
    raise SystemExit(f"FAILURE DETECTED: expected inserted=1 after payload_sha256=sha,; got {inserted}")
