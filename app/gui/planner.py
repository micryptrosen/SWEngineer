"""
Planner (Phase 2B)

Produces inert run plans (no execution).
Writes plans as evidence records (kind=RUN_PLAN) via GuiStore.

Design goals:
- Deterministic output structure
- Human-readable summary + machine JSON payload
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import List

from .store import EvidenceRecord, GuiStore, utc_now_iso


@dataclass(frozen=True)
class RunPlan:
    contract: str
    created_utc: str
    task_id: str
    task_title: str
    objective: str
    commands: List[str]
    required_gates: List[str]
    risk_flags: List[str]
    notes: str


def make_run_plan(task_id: str, task_title: str, notes: str) -> RunPlan:
    # Deterministic structure; content is intentionally conservative.
    return RunPlan(
        contract="runplan/1.0",
        created_utc=utc_now_iso(),
        task_id=task_id,
        task_title=task_title,
        objective=f"Plan changes for task {task_id}: {task_title}",
        commands=[
            "Set-Location -LiteralPath C:\\Dev\\CCP\\SWEngineer",
            "python -m tools.gates --mode local  # (or: py tools\\gates.py --mode local)",
            "# (add proposed commands here; do NOT execute from GUI)",
        ],
        required_gates=[
            "py tools\\gates.py --mode local",
        ],
        risk_flags=[
            "NO_EXECUTION_FROM_GUI",
            "HUMAN_REVIEW_REQUIRED",
        ],
        notes=(notes or "").strip(),
    )


def persist_run_plan(store: GuiStore, plan: RunPlan) -> EvidenceRecord:
    payload = json.dumps(asdict(plan), ensure_ascii=False, sort_keys=True, indent=2)
    summary = f"RUN_PLAN {plan.task_id}: {plan.task_title}"
    rec = EvidenceRecord(
        ev_id=f"E{len(store.read_evidence()) + 1:04d}",
        kind="RUN_PLAN",
        created_utc=utc_now_iso(),
        summary=summary[:80],
        body=payload,
    )
    store.append_evidence(rec)
    return rec
