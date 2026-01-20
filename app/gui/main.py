"""
SWEngineer GUI Shell (Phase 2A)

- Left navigation (Task Queue / Evidence)
- Task Queue UX stub: add mock tasks + view details (NO execution)
- Evidence UX stub: list mock evidence entries + view details
- No execution occurs on import (safe for tests/gates)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

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


@dataclass(frozen=True)
class TaskItem:
    task_id: str
    title: str
    status: str
    created_utc: str
    details: str


@dataclass(frozen=True)
class EvidenceItem:
    ev_id: str
    kind: str
    created_utc: str
    summary: str
    body: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TaskQueuePanel(QWidget):
    """
    Planner-only UI: enqueue tasks as inert records.
    No execution, no subprocess, no file writes beyond what the system already does.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._tasks: List[TaskItem] = []
        self._seq = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("Task Queue")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        outer.addWidget(header)

        hint = QLabel("Planner-only. Tasks are inert records (no execution).")
        hint.setStyleSheet("opacity: 0.85;")
        outer.addWidget(hint)

        # Input row
        row = QHBoxLayout()
        self.in_title = QLineEdit()
        self.in_title.setPlaceholderText("Task title (e.g., 'Add button to export evidence')")
        self.btn_add = QPushButton("Add Task (stub)")
        self.btn_add.clicked.connect(self._on_add_task)
        row.addWidget(self.in_title, 1)
        row.addWidget(self.btn_add)
        outer.addLayout(row)

        # Main split: list + detail
        split = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("Select a task to view details...")

        split.addWidget(self.list, 1)
        split.addWidget(self.detail, 2)
        outer.addLayout(split, 1)

        # Seed with one mock item
        self._add_task(
            title="Wire task planner surface (stub)",
            details="This is a placeholder task record. Execution remains gated by core engine.",
        )

    def _add_task(self, title: str, details: str) -> None:
        self._seq += 1
        tid = f"T{self._seq:04d}"
        item = TaskItem(
            task_id=tid,
            title=title.strip() or "(untitled)",
            status="PLANNED",
            created_utc=_utc_now_iso(),
            details=details.strip() or "",
        )
        self._tasks.append(item)

        lw = QListWidgetItem(f"{item.task_id}  {item.title}")
        lw.setData(Qt.UserRole, item.task_id)
        self.list.addItem(lw)
        self.list.setCurrentItem(lw)

    def _on_add_task(self) -> None:
        title = self.in_title.text()
        self.in_title.setText("")
        self._add_task(title=title, details="User-added task (stub). No execution performed.")

    def _on_select(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if current is None:
            self.detail.setPlainText("")
            return
        tid = current.data(Qt.UserRole)
        match = next((t for t in self._tasks if t.task_id == tid), None)
        if match is None:
            self.detail.setPlainText("")
            return

        self.detail.setPlainText(
            "\n".join(
                [
                    f"ID: {match.task_id}",
                    f"Status: {match.status}",
                    f"Created (UTC): {match.created_utc}",
                    "",
                    "Title:",
                    match.title,
                    "",
                    "Details:",
                    match.details,
                ]
            )
        )


class EvidencePanel(QWidget):
    """
    Evidence UI stub: display evidence records. In Phase 2A this is mock data.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._items: List[EvidenceItem] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("Evidence")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        outer.addWidget(header)

        hint = QLabel("Stub view. Later: show logs/artifacts produced by gated actions.")
        hint.setStyleSheet("opacity: 0.85;")
        outer.addWidget(hint)

        split = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setPlaceholderText("Select an evidence record to view...")

        split.addWidget(self.list, 1)
        split.addWidget(self.viewer, 2)
        outer.addLayout(split, 1)

        self._seed()

    def _seed(self) -> None:
        self._add(
            kind="GATE",
            summary="tools/gates.py --mode local (GREEN)",
            body="All checks passed.\nCI_YML_PARSE_OK\npytest: OK\n\n(Stub evidence record; no files read.)",
        )
        self._add(
            kind="UI",
            summary="GUI scaffold created (PySide6)",
            body="Left nav + stacked panels.\nTask Queue + Evidence panes (stub).\nNo execution.",
        )

    def _add(self, kind: str, summary: str, body: str) -> None:
        ev = EvidenceItem(
            ev_id=f"E{len(self._items)+1:04d}",
            kind=kind,
            created_utc=_utc_now_iso(),
            summary=summary,
            body=body,
        )
        self._items.append(ev)

        lw = QListWidgetItem(f"{ev.ev_id}  [{ev.kind}]  {ev.summary}")
        lw.setData(Qt.UserRole, ev.ev_id)
        self.list.addItem(lw)

        if self.list.count() == 1:
            self.list.setCurrentRow(0)

    def _on_select(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if current is None:
            self.viewer.setPlainText("")
            return
        ev_id = current.data(Qt.UserRole)
        match = next((e for e in self._items if e.ev_id == ev_id), None)
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

        root = QWidget(self)
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)

        # Left nav
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

        footer = QLabel("Execution is always gated.\n(UI is planner-only in Phase 2A.)")
        footer.setStyleSheet("opacity: 0.75; font-size: 11px;")
        nav_layout.addWidget(footer)

        # Main content panels (manual swap via setVisible)
        self.panel_taskq = TaskQueuePanel(root)
        self.panel_evidence = EvidencePanel(root)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.addWidget(self.panel_taskq, 1)
        content.addWidget(self.panel_evidence, 1)

        outer.addWidget(nav)
        outer.addLayout(content, 1)

        # Wiring
        self.btn_taskq.clicked.connect(lambda: self._show("taskq"))
        self.btn_evidence.clicked.connect(lambda: self._show("evidence"))
        self._show("taskq")

    def _show(self, which: str) -> None:
        self.panel_taskq.setVisible(which == "taskq")
        self.panel_evidence.setVisible(which == "evidence")


def run() -> int:
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
