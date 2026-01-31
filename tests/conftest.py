from __future__ import annotations

# Clean-clone determinism:
# - Ensure the *repo-under-test* src/ wins over any globally installed/editable copies.
# - Purge shadow sys.path entries and already-imported modules that are not from this repo.

import sys
from pathlib import Path


def _is_under(child: Path, parent: Path) -> bool:
    try:
        child = child.resolve()
        parent = parent.resolve()
        return parent == child or parent in child.parents
    except Exception:
        return False


def pytest_configure(config):
    repo = Path(__file__).resolve().parents[1]
    src = (repo / "src").resolve()

    # 1) Remove obvious shadow paths (editable installs / .pth injections) that point at OTHER SWEngineer roots.
    #    Keep stdlib + site-packages generally; only eject paths that look like SWEngineer but aren't this repo.
    cleaned = []
    for sp in list(sys.path):
        try:
            p = Path(sp).resolve()
        except Exception:
            cleaned.append(sp)
            continue

        s = str(p).lower()
        if "swengineer" in s:
            # If it's not under this repo, it is shadowing the clone-under-test.
            if not _is_under(p, repo):
                continue

        cleaned.append(sp)

    sys.path[:] = cleaned

    # 2) Force repo-under-test src precedence.
    if str(src) in sys.path:
        sys.path.remove(str(src))
    sys.path.insert(0, str(src))

    # 3) Purge already-imported shadow modules (if any) that were loaded from outside this repo.
    #    This protects against prior imports in the same interpreter session.
    prefixes = ("swe_", "app", "veristio_", "schemas")
    for name in list(sys.modules.keys()):
        if not name.startswith(prefixes):
            continue
        mod = sys.modules.get(name)
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        try:
            mf = Path(f).resolve()
        except Exception:
            continue
        if not _is_under(mf, repo):
            del sys.modules[name]

    # 4) Apply bootstrap from the repo-under-test.
    try:
        import swe_bootstrap
        swe_bootstrap.apply()
    except Exception as e:
        raise RuntimeError("FAILURE DETECTED: swe_bootstrap.apply() failed during pytest_configure") from e
