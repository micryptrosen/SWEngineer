"""
Planner (Phase 2B)

Produces inert run plans (no execution).
Writes plans + approvals + lifecycle markers + handoff contracts as evidence records.

Evidence kinds:
- RUN_PLAN
- RUN_PLAN_APPROVAL
- RUN_PLAN_SUPERSEDED
- RUN_HANDOFF
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import List, Optional

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
    supersedes_plan_ev_id: Optional[str] = None


@dataclass(frozen=True)
class RunPlanApproval:
    contract: str
    created_utc: str
    plan_ev_id: str
    reviewer: str
    decision: str  # APPROVED | REJECTED
    notes: str


@dataclass(frozen=True)
class RunPlanSuperseded:
    contract: str
    created_utc: str
    prior_plan_ev_id: str
    new_plan_ev_id: str
    reason: str


@dataclass(frozen=True)
class RunHandoff:
    contract: str
    created_utc: str
    plan_ev_id: str
    approval_ev_id: str
    runner_label: str
    required_gates: List[str]
    commands: List[str]
    statements: List[str]
    notes: str
    payload_sha256: str


def _json_loads_best_effort(s: str) -> dict:
    try:
        obj = json.loads(s or "{}")
        if isinstance(obj, dict):
            return obj
        return {}
    except Exception:
        return {}


def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_run_plan(task_id: str, task_title: str, notes: str) -> RunPlan:
    return RunPlan(
        contract="runplan/1.0",
        created_utc=utc_now_iso(),
        task_id=task_id,
        task_title=task_title,
        objective=f"Plan changes for task {task_id}: {task_title}",
        commands=[
            "Set-Location -LiteralPath C:\\Dev\\CCP\\SWEngineer",
            "py tools\\gates.py --mode local",
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
        supersedes_plan_ev_id=None,
    )


def persist_run_plan(store: GuiStore, plan: RunPlan) -> EvidenceRecord:
    payload = json.dumps(asdict(plan), ensure_ascii=False, sort_keys=True, indent=2)
    summary = f"RUN_PLAN {plan.task_id}: {plan.task_title}"
    if plan.supersedes_plan_ev_id:
        summary = (
            f"RUN_PLAN {plan.task_id}: {plan.task_title} (supersedes {plan.supersedes_plan_ev_id})"
        )
    rec = EvidenceRecord(
        ev_id=f"E{len(store.read_evidence()) + 1:04d}",
        kind="RUN_PLAN",
        created_utc=utc_now_iso(),
        summary=summary[:80],
        body=payload,
    )
    store.append_evidence(rec)
    return rec


def clone_run_plan(
    store: GuiStore, prior_plan_rec: EvidenceRecord, new_notes: str
) -> EvidenceRecord:
    prior = _json_loads_best_effort(prior_plan_rec.body)
    task_id = str(prior.get("task_id") or "T0000")
    task_title = str(prior.get("task_title") or "unknown")
    objective = str(prior.get("objective") or f"Plan changes for task {task_id}: {task_title}")
    commands = prior.get("commands") or []
    required_gates = prior.get("required_gates") or ["py tools\\gates.py --mode local"]
    risk_flags = prior.get("risk_flags") or ["NO_EXECUTION_FROM_GUI", "HUMAN_REVIEW_REQUIRED"]

    plan = RunPlan(
        contract="runplan/1.0",
        created_utc=utc_now_iso(),
        task_id=task_id,
        task_title=task_title,
        objective=objective,
        commands=list(commands),
        required_gates=list(required_gates),
        risk_flags=list(risk_flags),
        notes=(new_notes or "").strip(),
        supersedes_plan_ev_id=prior_plan_rec.ev_id,
    )
    return persist_run_plan(store, plan)


def make_approval(plan_ev_id: str, reviewer: str, decision: str, notes: str) -> RunPlanApproval:
    dec = (decision or "").strip().upper()
    if dec not in {"APPROVED", "REJECTED"}:
        dec = "APPROVED"
    return RunPlanApproval(
        contract="runplan_approval/1.0",
        created_utc=utc_now_iso(),
        plan_ev_id=plan_ev_id,
        reviewer=(reviewer or "").strip(),
        decision=dec,
        notes=(notes or "").strip(),
    )


def persist_approval(store: GuiStore, approval: RunPlanApproval) -> EvidenceRecord:
    payload = json.dumps(asdict(approval), ensure_ascii=False, sort_keys=True, indent=2)
    summary = f"RUN_PLAN_APPROVAL {approval.plan_ev_id}: {approval.decision} by {approval.reviewer or 'UNKNOWN'}"
    rec = EvidenceRecord(
        ev_id=f"E{len(store.read_evidence()) + 1:04d}",
        kind="RUN_PLAN_APPROVAL",
        created_utc=utc_now_iso(),
        summary=summary[:80],
        body=payload,
    )
    store.append_evidence(rec)
    return rec


def make_superseded(prior_plan_ev_id: str, new_plan_ev_id: str, reason: str) -> RunPlanSuperseded:
    return RunPlanSuperseded(
        contract="runplan_superseded/1.0",
        created_utc=utc_now_iso(),
        prior_plan_ev_id=prior_plan_ev_id,
        new_plan_ev_id=new_plan_ev_id,
        reason=(reason or "").strip(),
    )


def persist_superseded(store: GuiStore, marker: RunPlanSuperseded) -> EvidenceRecord:
    payload = json.dumps(asdict(marker), ensure_ascii=False, sort_keys=True, indent=2)
    summary = f"RUN_PLAN_SUPERSEDED {marker.prior_plan_ev_id} -> {marker.new_plan_ev_id}"
    rec = EvidenceRecord(
        ev_id=f"E{len(store.read_evidence()) + 1:04d}",
        kind="RUN_PLAN_SUPERSEDED",
        created_utc=utc_now_iso(),
        summary=summary[:80],
        body=payload,
    )
    store.append_evidence(rec)
    return rec


def _find_latest_approved_approval(store: GuiStore, plan_ev_id: str) -> Optional[EvidenceRecord]:
    # Search from newest to oldest.
    for rec in reversed(store.read_evidence()):
        if rec.kind != "RUN_PLAN_APPROVAL":
            continue
        obj = _json_loads_best_effort(rec.body)
        if str(obj.get("plan_ev_id") or "") != plan_ev_id:
            continue
        if str(obj.get("decision") or "").upper() == "APPROVED":
            return rec
    return None


def persist_handoff_from_plan(
    store: GuiStore, plan_rec: EvidenceRecord, runner_label: str, notes: str
) -> EvidenceRecord:
    if plan_rec.kind != "RUN_PLAN":
        raise ValueError("selected evidence is not RUN_PLAN")

    approval = _find_latest_approved_approval(store, plan_rec.ev_id)
    if approval is None:
        raise ValueError("no APPROVED approval found for selected RUN_PLAN")

    plan_obj = _json_loads_best_effort(plan_rec.body)
    required_gates = list(plan_obj.get("required_gates") or [])
    commands = list(plan_obj.get("commands") or [])

    # Build canonical payload (no sha), then hash it.
    payload_no_sha = {
        "contract": "run_handoff/1.0",
        "created_utc": utc_now_iso(),
        "plan_ev_id": plan_rec.ev_id,
        "approval_ev_id": approval.ev_id,
        "runner_label": (runner_label or "").strip() or "UNSPECIFIED_RUNNER",
        "required_gates": required_gates,
        "commands": commands,
        "statements": [
            "NO_EXECUTION_IN_GUI",
            "HANDOFF_IS_INERT_UNTIL_EXTERNAL_RUNNER_EXECUTES",
            "RUNNER_MUST_RE-RUN_GATES_BEFORE_ANY_COMMIT_OR_TAG",
            "EXECUTION_REQUIRES_HUMAN_AUTHORITY",
        ],
        "notes": (notes or "").strip(),
    }
    sha = _sha256_hex(_canonical_json(payload_no_sha))

    handoff = RunHandoff(
        contract=payload_no_sha["contract"],
        created_utc=payload_no_sha["created_utc"],
        plan_ev_id=payload_no_sha["plan_ev_id"],
        approval_ev_id=payload_no_sha["approval_ev_id"],
        runner_label=payload_no_sha["runner_label"],
        required_gates=payload_no_sha["required_gates"],
        commands=payload_no_sha["commands"],
        statements=payload_no_sha["statements"],
        notes=payload_no_sha["notes"],
        payload_sha256=sha,
    )

    payload = json.dumps(asdict(handoff), ensure_ascii=False, sort_keys=True, indent=2)
    summary = f"RUN_HANDOFF {plan_rec.ev_id} -> {handoff.runner_label}"
    rec = EvidenceRecord(
        ev_id=f"E{len(store.read_evidence()) + 1:04d}",
        kind="RUN_HANDOFF",
        created_utc=utc_now_iso(),
        summary=summary[:80],
        body=payload,
    )
    store.append_evidence(rec)
    return rec
