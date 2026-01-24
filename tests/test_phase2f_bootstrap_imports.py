from __future__ import annotations

def test_bootstrap_enables_runner_and_schemas_imports():
    # Canonical bootstrap must make imports work deterministically.
    import swe_bootstrap
    swe_bootstrap.apply()

    import swe_runner  # noqa: F401
    import swe_schemas  # noqa: F401

    # `swe_schemas` is a shim over vendor root `schemas`
    import schemas  # noqa: F401
