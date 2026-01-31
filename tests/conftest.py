# Clean-clone determinism:
# Ensure the *repo-under-test* src/ wins over any globally installed/editable copies.

from __future__ import annotations

import sys
from pathlib import Path

def pytest_configure(config):
    repo = Path(__file__).resolve().parents[1]
    src = (repo / "src").resolve()
    sys.path.insert(0, str(src))

    try:
        import swe_bootstrap
        swe_bootstrap.apply()
    except Exception as e:
        raise RuntimeError("FAILURE DETECTED: swe_bootstrap.apply() failed during pytest_configure") from e
