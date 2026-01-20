from pathlib import Path

from app.gui.store import EvidenceRecord, GuiStore, TaskEvent, utc_now_iso


def test_store_roundtrip(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    s.append_task_event(
        TaskEvent(
            task_id="T0001",
            event="CREATED",
            created_utc=utc_now_iso(),
            title="x",
            status="PLANNED",
            details="d",
        )
    )
    s.append_task_event(
        TaskEvent(
            task_id="T0001",
            event="STATUS",
            created_utc=utc_now_iso(),
            title="x",
            status="DONE",
            details="done",
        )
    )

    tasks = s.materialize_tasks()
    assert len(tasks) == 1
    assert tasks[0].task_id == "T0001"
    assert tasks[0].status == "DONE"

    s.append_evidence(
        EvidenceRecord(ev_id="E0001", kind="NOTE", created_utc=utc_now_iso(), summary="s", body="b")
    )
    ev = s.read_evidence()
    assert len(ev) == 1
    assert ev[0].ev_id == "E0001"
