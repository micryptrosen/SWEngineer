# Phase 4 / Step 4A (implemented as a test in 4C):
# Assert every contract id emitted/used by planner+runner resolves to a vendor schema.
#
# IMPORTANT:
# - This is a static scan gate (source-of-truth = code references).
# - Schema root must resolve to vendor/swe-schemas (canonical).
# - Fail hard and print missing contract ids.

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = [
    REPO_ROOT / "app",
    REPO_ROOT / "swe_runner",
]

# conservative contract id matcher: name/x.y[.z]
RX_CONTRACT = re.compile(r"\b([A-Za-z0-9_-]+/[0-9]+(?:\.[0-9]+)+)\b")


def _load_module_from_path(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load spec for {mod_name} from {path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = m
    spec.loader.exec_module(m)
    return m


def _resolve_schema_root_bootstrap_by_path() -> Path:
    candidates = list(REPO_ROOT.rglob("swe_bootstrap.py"))
    if not candidates:
        raise ModuleNotFoundError("swe_bootstrap.py not found under repo")
    candidates.sort(key=lambda p: (0 if p.parent == REPO_ROOT else 1, len(str(p))))
    bootstrap_path = candidates[0]

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    swe_bootstrap = _load_module_from_path("swe_bootstrap", bootstrap_path)
    if not hasattr(swe_bootstrap, "apply"):
        raise AttributeError(f"swe_bootstrap at {bootstrap_path} has no apply()")
    swe_bootstrap.apply()

    import swe_schemas  # type: ignore

    return Path(swe_schemas.resolve_schema_root()).resolve()


def _enumerate_contract_ids_static() -> list[str]:
    contracts: set[str] = set()
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in RX_CONTRACT.findall(text):
                contracts.add(m)
    return sorted(contracts)


def test_phase4_step4a_schema_coverage_gate():
    contracts = _enumerate_contract_ids_static()
    assert contracts, "no contract ids found in app/ or swe_runner/ (coverage gate meaningless)"

    schema_root = _resolve_schema_root_bootstrap_by_path()
    assert schema_root.exists(), f"canonical schema root missing: {schema_root}"
    assert str(schema_root).replace("/", "\\").endswith(r"\vendor\swe-schemas"), f"schema root not vendor/swe-schemas: {schema_root}"

    missing: list[str] = []
    for cid in contracts:
        name, ver = cid.split("/", 1)
        p1 = schema_root / name / f"{ver}.schema.json"
        p2 = schema_root / f"{name}-{ver}.schema.json"
        if not p1.exists() and not p2.exists():
            missing.append(cid)

    assert not missing, "MISSING_SCHEMAS:\n" + "\n".join(f" - {m}" for m in missing)
