# Phase 5 / Step 5A:
# Enforce canonical contract_id on real emitted contract artifacts (planner→handoff flow).
#
# This test SELF-GENERATES a fresh artifact set at runtime so it does not depend
# on historical _evidence contents.
#
# Rules:
# - Every contract artifact MUST include "contract_id" (string).
# - Alternate identifiers ("contract", "kind", "type") MUST NOT be used as substitutes.
# - Alternates may exist ONLY if contract_id exists.

from __future__ import annotations

import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALT_KEYS = ("contract", "kind", "type")


def _load_module_from_path(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load spec for {mod_name} from {path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = m
    spec.loader.exec_module(m)
    return m


def _apply_bootstrap_by_path():
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


def _emit_fresh_planner_handoff_artifacts(out_dir: Path) -> None:
    # Try multiple known entry points; whichever exists will be used.
    # We keep this tolerant to avoid coupling to one CLI surface.
    _apply_bootstrap_by_path()

    # Candidate functions (best-effort, no guesses beyond introspection)
    tried = []

    # 1) app.gui.planner: try to call a helper if present
    try:
        import app.gui.planner as planner  # type: ignore
        tried.append("app.gui.planner")
        # common pattern: planner.main(argv) or planner.run(...)
        if hasattr(planner, "main"):
            # attempt "main" with an out-dir flag if supported
            try:
                planner.main(["--out", str(out_dir)])
                return
            except TypeError:
                # maybe main() takes no args
                planner.main()
                return
        if hasattr(planner, "emit_for_tests"):
            planner.emit_for_tests(out_dir=str(out_dir))
            return
    except Exception:
        pass

    # 2) swe_runner: if it has a callable that emits handoff/plan
    try:
        import swe_runner  # type: ignore
        tried.append("swe_runner")
        if hasattr(swe_runner, "emit_for_tests"):
            swe_runner.emit_for_tests(out_dir=str(out_dir))
            return
    except Exception:
        pass

    raise AssertionError("could not emit fresh artifacts; tried: " + ", ".join(tried))


def _collect_json(out_dir) -> list[Path]:
    out_dir = Path(out_dir)
    files = sorted(out_dir.rglob("*.json"))
    if not files:
        raise AssertionError(f"no json artifacts emitted to: {out_dir}")
    return files


def test_phase5_step5a_contract_id_normalization(tmp_path: Path):
    # deterministically allocate a per-test output directory
    out_dir = tmp_path / ("phase5a_artifacts_" + uuid.uuid4().hex)
    out_dir.mkdir(parents=True, exist_ok=True)

    _emit_fresh_planner_handoff_artifacts(out_dir)

    artifacts = _collect_json(out_dir)

    failures: list[str] = []
    for p in artifacts:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            failures.append(f"{p.name}: invalid json ({e})")
            continue

        has_contract_id = isinstance(data.get("contract_id"), str) and bool(data.get("contract_id"))
        alt_present = [k for k in ALT_KEYS if k in data]

        if not has_contract_id:
            failures.append(f"{p.name}: missing required contract_id")

        if alt_present and not has_contract_id:
            failures.append(f"{p.name}: uses alternate keys {alt_present} without contract_id")

    assert not failures, "CONTRACT_ID_NORMALIZATION_FAILURES:\n" + "\n".join(f" - {f}" for f in failures)
