from __future__ import annotations
from pathlib import Path

root = Path(r'C:\Dev\CCP\SWEngineer')
p = root / 'tools' / 'gates.py'
s = p.read_text(encoding='utf-8')

# Idempotence guard
    print('NOOP=validate_ci already present')
else:
    if anchor not in s:
        raise SystemExit('FAILURE DETECTED: ruff anchor not found; aborting patch.')
    insert = (
        anchor
    )
    s = s.replace(anchor, insert, 1)
    p.write_text(s, encoding='utf-8', newline='\\n')
    print('PATCHED=tools/gates.py')
