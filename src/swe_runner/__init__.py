from __future__ import annotations

"""
swe_runner (minimal stub)

Purpose (Phase 3 recovery):
- Provide a deterministic import target for `import swe_runner` after `swe_bootstrap.apply()`.
- Keep import-time side effects at ZERO.
- Future Phase 3 work can replace/expand this with the real runner implementation/submodule.
"""

__all__ = ["__version__", "about"]
__version__ = "0.0.0-dev"

def about() -> str:
    return "swe_runner stub (Phase 3 recovery): import-safe, side-effect free."
