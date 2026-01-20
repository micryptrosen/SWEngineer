"""
SWEngineer GUI Shell (Phase 2A4)

- Planner-only Task Queue with event-sourced persistence
- Evidence stream with Add Note (append-only)
- No engine execution
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .store import EvidenceRecord, GuiStore, TaskEvent, utc_now_iso


def _safe(s: str) -> str:
    return (s or "").strip()


class TaskQueuePanel(QWidget):
    def __init__(self, store: GuiStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("Task Queue")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        outer.addWidget(header)

        hint = QLabel("Planner-only. Tasks are inert records. Append-only task events.")
        hint.setStyleSheet("opacity: 0.85;")
        outer.addWidget(hint)

        row = QHBoxLayout()
        self.in_title = QLineEdit()
        self.in_title.setPlaceholderText("Task title…")
        self.btn_add = QPushButton("Add Task")
        self.btn_add.clicked.connect(self._on_add_task)
        self.btn_done = QPushButton("Mark Done")
        self.btn_done.clicked.connect(self._on_mark_done)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.reload)

        row.addWidget(self.in_title, 1)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_done)
        row.addWidget(self.btn_refresh)
        outer.addLayout(row)

        split = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("Select a task…")

        split.addWidget(self.list, 1)
        split.addWidget(self.detail, 2)
        outer.addLayout(split, 1)

        self.reload()
        if self.list.count() == 0:
            self._append_create(
                "Wire event-sourced tasks", "Append-only task events under data/task_events.jsonl."
            )
            self.reload()

    def _next_task_id(self) -> str:
        st = self.store.materialize_tasks()
        return f"T{len(st) + 1:04d}"

    def _next_ev_id(self) -> str:
        ev = self.store.read_evidence()
        return f"E{len(ev) + 1:04d}"

    def _append_create(self, title: str, details: str) -> None:
        tid = self._next_task_id()
        ev = TaskEvent(
            task_id=tid,
            event="CREATED",
            created_utc=utc_now_iso(),
            title=_safe(title) or "(untitled)",
            status="PLANNED",
            details=_safe(details),
        )
        self.store.append_task_event(ev)
        self.store.append_evidence(
            EvidenceRecord(
                ev_id=self._next_ev_id(),
                kind="UI",
                created_utc=utc_now_iso(),
                summary=f"Task created: {tid} {ev.title}",
                body=str(ev),
            )
        )

    def _append_statuss(self, tid: str, title: str, status: str, details: str) -> None:
        ev = TaskEvent(
            task_id=tid,
            event="STATUS",
            created_utc=utc_now_iso(),
            title=title,
            status=status,
            details=_safe(details),
        )
        self.store.append_task_event(ev)
        self.store.append_evidence(
            EvidenceRecord(
                ev_id=self._next_ev_id(),
                kind="UI",
                created_utc=utc_now_iso(),
                summary=f"Task status: {tid} -> {status}",
                body=str(ev),
            )
        )

    def reload(self) -> None:
        self.list.clear()
        tasks = self.store.materialize_tasks()
        for t in tasks:
            lw = QListWidgetItem(f"{t.task_id}  [{t.status}]  {t.title}")
            lw.setData(Qt.UserRole, t.task_id)
            self.list.addItem(lw)
        if self.list.count() > 0:
            self.list.setCurrentRow(self.list.count() - 1)

    def _selected_task(self) -> TaskEvent | None:
        cur = self.list.currentItem()
        if cur is None:
            return None
        tid = cur.data(Qt.UserRole)
        for t in self.store.materialize_tasks():
            if t.task_id == tid:
                return t
        return None

    def _on_add_task(self) -> None:
        title = self.in_title.text()
        self.in_title.setText("")
        self._append_create(title, "User-added task (planner-only).")
        self.reload()

    def _on_mark_done(self) -> None:
        t = self._selected_task()
        if t is None:
            return
        if t.status == "DONE":
            return
        self._append_status(t.task_id, t.title, "DONE", "Marked DONE in GUI (planner-only).")
        self.reload()

    def _append_status(self, task_id: str, title: str, status: str, details: str) -> None:
        ev = TaskEvent(
            task_id=task_id,
            event="STATUS",
            created_utc=utc_now_iso(),
            title=title,
            status=status,
            details=_safe(details),
        )
        self.store.append_task_event(ev)
        self.store.append_evidence(
            EvidenceRecord(
                ev_id=self._next_ev_id(),
                kind="UI",
                created_utc=utc_now_iso(),
                summary=f"Task status: {task_id} -> {status}",
                body=str(ev),
            )
        )

    def _on_select(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if current is None:
            self.detail.setPlainText("")
            return
        tid = current.data(Qt.UserRole)
        state = next((t for t in self.store.materialize_tasks() if t.task_id == tid), None)
        if state is None:
            self.detail.setPlainText("")
            return
        self.detail.setPlainText(
            "\n".join(
                [
                    f"ID: {state.task_id}",
                    f"Status: {state.status}",
                    f"Last Updated (UTC): {state.created_utc}",
                    "",
                    "Title:",
                    state.title,
                    "",
                    "Details:",
                    state.details,
                ]
            )
        )


class EvidencePanel(QWidget):
    def __init__(self, store: GuiStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("Evidence")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        outer.addWidget(header)

        hint = QLabel("Append-only evidence stream (local). Add notes; no execution.")
        hint.setStyleSheet("opacity: 0.85;")
        outer.addWidget(hint)

        note_row = QHBoxLayout()
        self.in_note = QLineEdit()
        self.in_note.setPlaceholderText("Add evidence note…")
        self.btn_note = QPushButton("Add Note")
        self.btn_note.clicked.connect(self._on_add_note)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.reload)
        note_row.addWidget(self.in_note, 1)
        note_row.addWidget(self.btn_note)
        note_row.addWidget(self.btn_refresh)
        outer.addLayout(note_row)

        split = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setPlaceholderText("Select evidence…")

        split.addWidget(self.list, 1)
        split.addWidget(self.viewer, 2)
        outer.addLayout(split, 1)

        self.reload()
        if self.list.count() == 0:
            self._append_note("Evidence stream initialized (Phase 2A4).")
            self.reload()

    def _next_ev_id(self) -> str:
        ev = self.store.read_evidence()
        return f"E{len(ev) + 1:04d}"

    def _append_note(self, note: str) -> None:
        rec = EvidenceRecord(
            ev_id=self._next_ev_id(),
            kind="NOTE",
            created_utc=utc_now_iso(),
            summary=_safe(note)[:80] or "(note)",
            body=_safe(note),
        )
        self.store.append_evidence(rec)

    def _on_add_note(self) -> None:
        note = self.in_note.text()
        self.in_note.setText("")
        if not _safe(note):
            return
        self._append_note(note)
        self.reload()

    def reload(self) -> None:
        self.list.clear()
        items = self.store.read_evidence()
        for e in items:
            lw = QListWidgetItem(f"{e.ev_id}  [{e.kind}]  {e.summary}")
            lw.setData(Qt.UserRole, e.ev_id)
            self.list.addItem(lw)
        if self.list.count() > 0:
            self.list.setCurrentRow(self.list.count() - 1)

    def _on_select(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if current is None:
            self.viewer.setPlainText("")
            return
        ev_id = current.data(Qt.UserRole)
        match = next((e for e in self.store.read_evidence() if e.ev_id == ev_id), None)
        if match is None:
            self.viewer.setPlainText("")
            return
        self.viewer.setPlainText(
            "\n".join(
                [
                    f"ID: {match.ev_id}",
                    f"Kind: {match.kind}",
                    f"Created (UTC): {match.created_utc}",
                    "",
                    "Summary:",
                    match.summary,
                    "",
                    "Body:",
                    match.body,
                ]
            )
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SWEngineer — GUI Scaffold (Phase 2A)")
        self.resize(1100, 700)

        self.store = GuiStore()

        root = QWidget(self)
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)

        nav = QFrame(root)
        nav.setFrameShape(QFrame.StyledPanel)
        nav.setFixedWidth(240)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(12, 12, 12, 12)
        nav_layout.setSpacing(8)

        title = QLabel("SWEngineer")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        nav_layout.addWidget(title)

        subtitle = QLabel("Phase 2A — Scaffold")
        subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subtitle.setStyleSheet("opacity: 0.8;")
        nav_layout.addWidget(subtitle)

        nav_layout.addSpacing(10)

        self.btn_taskq = QPushButton("Task Queue")
        self.btn_evidence = QPushButton("Evidence")
        nav_layout.addWidget(self.btn_taskq)
        nav_layout.addWidget(self.btn_evidence)
        nav_layout.addStretch(1)

        footer = QLabel("Execution is always gated.\nGUI is planner-only in Phase 2A.")
        footer.setStyleSheet("opacity: 0.75; font-size: 11px;")
        nav_layout.addWidget(footer)

        self.panel_taskq = TaskQueuePanel(self.store, root)
        self.panel_evidence = EvidencePanel(self.store, root)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.addWidget(self.panel_taskq, 1)
        content.addWidget(self.panel_evidence, 1)

        outer.addWidget(nav)
        outer.addLayout(content, 1)

        self.btn_taskq.clicked.connect(lambda: self._show("taskq"))
        self.btn_evidence.clicked.connect(lambda: self._show("evidence"))
        self._show("taskq")

    def _show(self, which: str) -> None:
        self.panel_taskq.setVisible(which == "taskq")
        self.panel_evidence.setVisible(which == "evidence")
        if which == "taskq":
            self.panel_taskq.reload()
        else:
            self.panel_evidence.reload()


def run() -> int:
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
