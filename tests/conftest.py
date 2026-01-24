from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
VENDOR = REPO / "vendor" / "swe-schemas"

def _ins(p: Path) -> None:
    s = str(p)
    if p.exists() and s not in sys.path:
        sys.path.insert(0, s)

# Priority: vendor first, then src
_ins(VENDOR)
_ins(SRC)
