from pathlib import Path

from app.gui.store import EvidenceRecord, GuiStore, TaskRecord, utc_now_iso


def test_store_roundtrip(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    t = TaskRecord(
        task_id="T0001", title="x", status="PLANNED", created_utc=utc_now_iso(), details="d"
    )
    s.append_task(t)
    tasks = s.read_tasks()
    assert len(tasks) == 1
    assert tasks[0].task_id == "T0001"

    e = EvidenceRecord(ev_id="E0001", kind="GATE", created_utc=utc_now_iso(), summary="s", body="b")
    s.append_evidence(e)
    ev = s.read_evidence()
    assert len(ev) == 1
    assert ev[0].ev_id == "E0001"
