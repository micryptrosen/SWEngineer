"""
SWEngineer GUI Shell

Planner-only shell:
- Task Queue (event-sourced, append-only)
- Evidence stream (append-only)
- Evidence tools:
  - Paste-in Gate Snapshot (does NOT execute gates)
  - Session template helpers (Start-Day / Close / Note)
- Planner:
  - Generate Run Plan (does NOT execute)
  - Approve Run Plan (human sign-off; does NOT execute)
  - Clone Run Plan (creates new plan that supersedes prior; append-only marker)

No engine execution.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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

from .planner import (
    clone_run_plan,
    make_approval,
    make_run_plan,
    make_superseded,
    persist_approval,
    persist_run_plan,
    persist_superseded,
)
from .store import EvidenceRecord, GuiStore, TaskEvent, utc_now_iso


def _safe(s: str) -> str:
    return (s or "").strip()


def _truncate(s: str, n: int) -> str:
    s = _safe(s)
    return s if len(s) <= n else (s[: n - 1] + "…")


def _template_start_day() -> str:
    return "\n".join(
        [
            "START-DAY DECLARATION",
            "",
            "EFFORT: SWEngineer — GUI Scaffold",
            "AUTHORITY: Michael A. Trosen (Operator)",
            "STATE: ACTIVE",
            "REPO: C:\\Dev\\CCP\\SWEngineer (origin: micryptrosen/SWEngineer.git)",
            "BASELINE: Gates locked (PUBLISH=GREEN)",
            "",
            "Objective",
            "",
            "- (fill in)",
            "",
            "Non-negotiables",
            "",
            "- Gates remain authoritative (tools/gates.py)",
            "- No commits without green gates",
            "- Paste-safe + idempotent workflow",
            "",
            "Next best step",
            "",
            "- (fill in)",
        ]
    )


def _template_close() -> str:
    return "\n".join(
        [
            "CLOSE DECLARATION",
            "",
            "EFFORT: SWEngineer — GUI Scaffold",
            "STATE: CLOSED",
            "RESULT: PUBLISH=GREEN",
            "",
            "Artifacts",
            "",
            "- Tag: (paste tag)",
            "- Notes: (what changed)",
            "",
            "Next",
            "",
            "- (fill in)",
        ]
    )


def _template_note() -> str:
    return "\n".join(["NOTE", "", "- (write note)"])


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
        self.btn_plan = QPushButton("Generate Run Plan")
        self.btn_plan.clicked.connect(self._on_generate_plan)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.reload)

        row.addWidget(self.in_title, 1)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_done)
        row.addWidget(self.btn_plan)
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
                "Clone a Run Plan", "Create a run plan, then clone/supersede it in Evidence."
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
        if t is None or t.status == "DONE":
            return
        self._append_status(t.task_id, t.title, "DONE", "Marked DONE in GUI (planner-only).")
        self.reload()

    def _on_generate_plan(self) -> None:
        t = self._selected_task()
        if t is None:
            return
        plan = make_run_plan(t.task_id, t.title, notes=t.details)
        persist_run_plan(self.store, plan)
        self.detail.setPlainText(
            self.detail.toPlainText() + "\n\nRun Plan saved to Evidence (kind=RUN_PLAN)."
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

        hint = QLabel(
            "Append-only evidence stream (local). Approvals and supersedes are human-only."
        )
        hint.setStyleSheet("opacity: 0.85;")
        outer.addWidget(hint)

        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("Template:"))
        self.tpl = QComboBox()
        self.tpl.addItems(["Note", "Start-Day", "Close"])
        self.btn_apply_tpl = QPushButton("Apply Template")
        self.btn_apply_tpl.clicked.connect(self._on_apply_template)
        tpl_row.addWidget(self.tpl)
        tpl_row.addWidget(self.btn_apply_tpl)
        tpl_row.addStretch(1)
        outer.addLayout(tpl_row)

        appr = QHBoxLayout()
        self.in_reviewer = QLineEdit()
        self.in_reviewer.setPlaceholderText("Reviewer name…")
        self.sel_decision = QComboBox()
        self.sel_decision.addItems(["APPROVED", "REJECTED"])
        self.btn_approve = QPushButton("Approve Selected RUN_PLAN")
        self.btn_approve.clicked.connect(self._on_approve_selected_plan)
        appr.addWidget(QLabel("Approval:"))
        appr.addWidget(self.in_reviewer, 1)
        appr.addWidget(self.sel_decision)
        appr.addWidget(self.btn_approve)
        outer.addLayout(appr)

        clone_row = QHBoxLayout()
        self.btn_clone = QPushButton("Clone Selected RUN_PLAN (supersede)")
        self.btn_clone.clicked.connect(self._on_clone_selected_plan)
        clone_row.addWidget(self.btn_clone)
        clone_row.addStretch(1)
        outer.addLayout(clone_row)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText(
            "Write notes (or paste gate output). For Clone: paste new notes here."
        )
        outer.addWidget(self.editor, 1)

        actions = QHBoxLayout()
        self.btn_save_note = QPushButton("Save Note")
        self.btn_save_note.clicked.connect(self._on_save_note)
        self.btn_save_gate = QPushButton("Save Gate Snapshot")
        self.btn_save_gate.clicked.connect(self._on_save_gate)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.reload)

        actions.addWidget(self.btn_save_note)
        actions.addWidget(self.btn_save_gate)
        actions.addWidget(self.btn_refresh)
        actions.addStretch(1)
        outer.addLayout(actions)

        split = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setPlaceholderText("Select evidence…")

        split.addWidget(self.list, 1)
        split.addWidget(self.viewer, 2)
        outer.addLayout(split, 2)

        self.reload()
        if self.list.count() == 0:
            self._append_note("Evidence tools initialized.")
            self.reload()

    def _next_ev_id(self) -> str:
        ev = self.store.read_evidence()
        return f"E{len(ev) + 1:04d}"

    def _append_note(self, note: str) -> None:
        rec = EvidenceRecord(
            ev_id=self._next_ev_id(),
            kind="NOTE",
            created_utc=utc_now_iso(),
            summary=_truncate(note, 80) or "(note)",
            body=_safe(note),
        )
        self.store.append_evidence(rec)

    def _append_gate_snapshot(self, txt: str) -> None:
        body = _safe(txt)
        rec = EvidenceRecord(
            ev_id=self._next_ev_id(),
            kind="GATE_SNAPSHOT",
            created_utc=utc_now_iso(),
            summary=_truncate(body.splitlines()[0] if body else "Gate Snapshot", 80),
            body=body,
        )
        self.store.append_evidence(rec)

    def _on_apply_template(self) -> None:
        choice = self.tpl.currentText()
        if choice == "Start-Day":
            self.editor.setPlainText(_template_start_day())
        elif choice == "Close":
            self.editor.setPlainText(_template_close())
        else:
            self.editor.setPlainText(_template_note())

    def _on_save_note(self) -> None:
        txt = self.editor.toPlainText()
        if not _safe(txt):
            return
        self._append_note(txt)
        self.editor.setPlainText("")
        self.reload()

    def _on_save_gate(self) -> None:
        txt = self.editor.toPlainText()
        if not _safe(txt):
            return
        self._append_gate_snapshot(txt)
        self.editor.setPlainText("")
        self.reload()

    def _selected_evidence(self) -> EvidenceRecord | None:
        cur = self.list.currentItem()
        if cur is None:
            return None
        ev_id = cur.data(Qt.UserRole)
        return next((e for e in self.store.read_evidence() if e.ev_id == ev_id), None)

    def _on_approve_selected_plan(self) -> None:
        sel = self._selected_evidence()
        if sel is None or sel.kind != "RUN_PLAN":
            return
        reviewer = _safe(self.in_reviewer.text()) or "UNKNOWN"
        decision = self.sel_decision.currentText()
        notes = self.editor.toPlainText()
        appr = make_approval(sel.ev_id, reviewer, decision, notes)
        persist_approval(self.store, appr)
        self.editor.setPlainText("")
        self.reload()

    def _on_clone_selected_plan(self) -> None:
        sel = self._selected_evidence()
        if sel is None or sel.kind != "RUN_PLAN":
            return
        new_notes = self.editor.toPlainText()
        new_plan = clone_run_plan(self.store, sel, new_notes=new_notes)
        marker = make_superseded(
            sel.ev_id, new_plan.ev_id, reason="Cloned in GUI; prior plan superseded."
        )
        persist_superseded(self.store, marker)
        self.editor.setPlainText("")
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
        self.setWindowTitle("SWEngineer — GUI Scaffold")
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

        subtitle = QLabel("Planner-only (Phase 2B)")
        subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subtitle.setStyleSheet("opacity: 0.8;")
        nav_layout.addWidget(subtitle)

        nav_layout.addSpacing(10)

        self.btn_taskq = QPushButton("Task Queue")
        self.btn_evidence = QPushButton("Evidence")
        nav_layout.addWidget(self.btn_taskq)
        nav_layout.addWidget(self.btn_evidence)
        nav_layout.addStretch(1)

        footer = QLabel("Execution is always gated.\nGUI never executes commands.")
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
