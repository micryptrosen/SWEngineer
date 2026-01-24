from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd().resolve()
P = ROOT / "app" / "gui" / "planner.py"
if not P.exists():
    raise SystemExit(f"FAILURE DETECTED: missing {P}")

lines = P.read_text(encoding="utf-8").splitlines()

# 1) Comment out premature validate_payload(payload_no_sha)
removed_no_sha = 0
out = []
for line in lines:
    if "validate_payload(payload_no_sha)" in line and not line.lstrip().startswith("#"):
        out.append(line.replace("validate_payload(payload_no_sha)", "# validate_payload(payload_no_sha)  # deferred: schema requires payload_sha256"))
        removed_no_sha += 1
    else:
        out.append(line)

if removed_no_sha != 1:
    raise SystemExit(f"FAILURE DETECTED: expected exactly 1 validate_payload(payload_no_sha); found {removed_no_sha}")

# 2) Remove any validate_payload(...) accidentally inserted INSIDE RunHandoff(...) args
#    (we only remove those occurring between 'handoff = RunHandoff(' and its closing '    )')
in_handoff = False
removed_inside = 0
clean = []

for line in out:
    if "handoff = RunHandoff(" in line:
        in_handoff = True
        clean.append(line)
        continue

    if in_handoff:
        if line.strip() == ")":
            in_handoff = False
            clean.append(line)
            continue
        if "validate_payload(" in line:
            removed_inside += 1
            # skip this line
            continue

    clean.append(line)

if removed_inside < 1:
    # Not fatal, but we expect at least 1 based on the SyntaxError.
    # Keep it strict so we don't silently fail.
    raise SystemExit("FAILURE DETECTED: expected to remove at least 1 validate_payload(...) inside RunHandoff(...); removed_inside=0")

# 3) Insert validate_payload(asdict(handoff)) immediately AFTER the RunHandoff(...) call closes.
#    Find 'handoff = RunHandoff(' then the next line that is exactly '    )' (4 spaces + ')').
inserted_after = 0
final = []
i = 0
while i < len(clean):
    line = clean[i]
    final.append(line)

    if "handoff = RunHandoff(" in line:
        j = i + 1
        close_idx = None
        while j < len(clean):
            if clean[j] == "    )":
                close_idx = j
                break
            j += 1

        if close_idx is None:
            raise SystemExit("FAILURE DETECTED: could not find closing '    )' for handoff RunHandoff(...) call")

        # copy through the close line (we already copied current i; now copy i+1..close_idx)
        k = i + 1
        while k <= close_idx:
            final.append(clean[k])
            k += 1

        # Insert validation after close line (only once)
        final.append("")
        final.append("    # Validate final handoff payload (includes payload_sha256)")
        final.append("    validate_payload(asdict(handoff))")
        inserted_after += 1

        i = close_idx + 1
        continue

    i += 1

if inserted_after != 1:
    raise SystemExit(f"FAILURE DETECTED: expected to insert validation after handoff exactly once; inserted_after={inserted_after}")

P.write_text("\n".join(final) + "\n", encoding="utf-8", newline="\n")
print("PLANNER_HANDOFF_VALIDATION_FIXED=GREEN")
