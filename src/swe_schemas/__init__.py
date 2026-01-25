r"""
swe_schemas (shim)

Canonical import name used by SWEngineer tooling to reference the vendored schema library.

Vendor payload lives at:
  C:\Dev\CCP\SWEngineer\vendor\swe-schemas\schemas

That vendor library's import root is `schemas`, so we provide `swe_schemas` as a stable alias.

Contract:
- `import swe_schemas` MUST succeed
- `import swe_schemas.<x>` MUST mirror `import schemas.<x>` (when such submodules exist)
- No runtime side effects beyond import aliasing
"""
from __future__ import annotations
from pathlib import Path

import importlib
import sys

# Import real vendor root package
_real = importlib.import_module("schemas")

# Expose `schemas` attributes via `swe_schemas`
def __getattr__(name: str):
    return getattr(_real, name)

def __dir__():
    return sorted(set(dir(_real)))

# Ensure sys.modules aliasing supports submodule imports.
# If a consumer imports `swe_schemas.foo`, we want Python to find `schemas.foo`.
# We do this by making `swe_schemas` behave like a package whose __path__ matches `schemas.__path__`.
__path__ = getattr(_real, "__path__", None)  # type: ignore[assignment]
__all__ = getattr(_real, "__all__", [])
sys.modules.setdefault("swe_schemas", sys.modules[__name__])

# --- Phase 3 Step 3D: required public API ---
def resolve_schema_root(schema_root=None) -> Path:
    """Return the canonical schema root.

    Default: vendor-backed schemas at vendor/swe-schemas.
    Optional override: a caller-supplied path.
    """
    if schema_root is not None:
        return Path(schema_root)
    return Path(r"C:\Dev\CCP\SWEngineer") / "vendor" / "swe-schemas"

