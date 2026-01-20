"""
GUI persistence (Phase 2A4)

Event-sourced, append-only JSONL.
- tasks: data/task_events.jsonl
- evidence: evidence/evidence.jsonl

No execution. No engine invocation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    event: str  # CREATED | STATUS
    created_utc: str
    title: str
    status: str
    details: str


@dataclass(frozen=True)
class EvidenceRecord:
    ev_id: str
    kind: str
    created_utc: str
    summary: str
    body: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, obj: dict) -> None:
    _ensure_parent(path)
    line = json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            out.append(json.loads(raw))
    return out


class GuiStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.root = base_dir or _repo_root()
        self.task_events_path = self.root / "data" / "task_events.jsonl"
        self.evidence_path = self.root / "evidence" / "evidence.jsonl"

    # ----_toggle: tasks ----
    def append_task_event(self, ev: TaskEvent) -> None:
        _append_jsonl(self.task_events_path, asdict(ev))

    def read_task_events(self) -> list[TaskEvent]:
        return [TaskEvent(**r) for r in _read_jsonl(self.task_events_path)]

    def materialize_tasks(self) -> list[TaskEvent]:
        """
        Returns last-known state per task_id as TaskEvent rows (event='STATE').
        """
        events = self.read_task_events()
        state: dict[str, TaskEvent] = {}
        for e in events:
            state[e.task_id] = TaskEvent(
                task_id=e.task_id,
                event="STATE",
                created_utc=e.created_utc,
                title=e.title,
                status=e.status,
                details=e.details,
            )
        return [state[k] for k in sorted(state.keys())]

    # ---- evidence ----
    def append_evidence(self, rec: EvidenceRecord) -> None:
        _append_jsonl(self.evidence_path, asdict(rec))

    def read_evidence(self) -> list[EvidenceRecord]:
        return [EvidenceRecord(**r) for r in _read_jsonl(self.evidence_path)]
