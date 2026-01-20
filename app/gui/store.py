"""
GUI persistence (Phase 2A3)

- Repo-local, append-only JSONL stores
- No execution. No engine invocation.
- Designed to be deterministic and testable.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    title: str
    status: str
    created_utc: str
    details: str


@dataclass(frozen=True)
class EvidenceRecord:
    ev_id: str
    kind: str
    created_utc: str
    summary: str
    body: str


def _repo_root() -> Path:
    # app/gui/store.py -> repo root at 3 levels up: app/gui/ -> app/ -> repo
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
    """
    Repo-local store:
      data/tasks.jsonl
      evidence/evidence.jsonl
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.root = base_dir or _repo_root()
        self.tasks_path = self.root / "data" / "tasks.jsonl"
        self.evidence_path = self.root / "evidence" / "evidence.jsonl"

    # ---- tasks ----
    def append_task(self, rec: TaskRecord) -> None:
        _append_jsonl(self.tasks_path, asdict(rec))

    def read_tasks(self) -> list[TaskRecord]:
        rows = _read_jsonl(self.tasks_path)
        return [TaskRecord(**r) for r in rows]

    # ---- evidence ----
    def append_evidence(self, rec: EvidenceRecord) -> None:
        _append_jsonl(self.evidence_path, asdict(rec))

    def read_evidence(self) -> list[EvidenceRecord]:
        rows = _read_jsonl(self.evidence_path)
        return [EvidenceRecord(**r) for r in rows]
