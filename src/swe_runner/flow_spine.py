"""SWEngineer Flow Spine (Phase1F)

Contract: stable internal surface for ordered execution:
  build_plan -> validate_plan -> execute_plan -> emit_evidence -> publish_if_allowed

Phase1E: bound to canonical swe_schemas plumbing (isolation-safe).
Phase1F: introduces optional delegation to app.gui.planner spine hooks (scaffold only).
Default behavior remains unchanged unless caller explicitly routes here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import swe_schemas  # canonical plumbing


def resolve_schema_root() -> str:
    return swe_schemas.resolve_schema_root()


@dataclass(frozen=True)
class FlowResult:
    ok: bool
    summary: str
    artifacts: Optional[Dict[str, Any]] = None


class SpineNotBoundError(RuntimeError):
    pass


def _try_import_planner_hooks():
    """
    Import the planner nucleus and return its hook functions if present.
    This import is intentionally inside the function to avoid side effects at import time.
    """
    try:
        from app.gui import planner as _planner  # type: ignore
    except Exception as e:
        raise SpineNotBoundError(f"planner import failed: {e}") from e

    need = ("spine_build_plan", "spine_validate_plan", "spine_execute_plan")
    missing = [n for n in need if not hasattr(_planner, n)]
    if missing:
        raise SpineNotBoundError("planner spine hooks missing: " + ", ".join(missing))

    return _planner.spine_build_plan, _planner.spine_validate_plan, _planner.spine_execute_plan


def run_flow(intent: Dict[str, Any]) -> FlowResult:
    """
    Phase1F behavior:
      - Delegates to planner spine hooks if they exist.
      - If not bound yet, returns a non-fatal placeholder result (no exceptions) to preserve stability.
    """
    try:
        build_plan, validate_plan, execute_plan = _try_import_planner_hooks()
        plan = build_plan(intent)
        vplan = validate_plan(plan)
        artifacts = execute_plan(vplan)
        return FlowResult(ok=True, summary="flow spine delegated to planner hooks (Phase1F)", artifacts=artifacts)
    except SpineNotBoundError as e:
        # Non-fatal for Phase1F: we are scaffolding only.
        return FlowResult(ok=True, summary="flow spine scaffold (Phase1F): " + str(e), artifacts=None)
