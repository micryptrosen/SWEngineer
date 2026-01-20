"""
SWEngineer GUI Shell (Phase 2A)

- Left navigation (Task Queue / Evidence)
- Central stacked panel (stubs only)
- No execution occurs on import (safe for tests/gates)
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class TaskQueuePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Task Queue (stub)"))
        layout.addWidget(QLabel("Planner-only surface here (no execution)."))
        layout.addStretch(1)


class EvidencePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Evidence (stub)"))
        layout.addWidget(QLabel("Logs / artifacts surfaced here."))
        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SWEngineer — GUI Scaffold (Phase 2A)")
        self.resize(1100, 700)

        root = QWidget(self)
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)

        # Left nav
        nav = QWidget(root)
        nav.setFixedWidth(220)
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

        # Main content stack
        self.stack = QStackedWidget(root)
        self.panel_taskq = TaskQueuePanel(self.stack)
        self.panel_evidence = EvidencePanel(self.stack)
        self.stack.addWidget(self.panel_taskq)
        self.stack.addWidget(self.panel_evidence)

        outer.addWidget(nav)
        outer.addWidget(self.stack, 1)

        # Wiring
        self.btn_taskq.clicked.connect(lambda: self.stack.setCurrentWidget(self.panel_taskq))
        self.btn_evidence.clicked.connect(lambda: self.stack.setCurrentWidget(self.panel_evidence))
        self.stack.setCurrentWidget(self.panel_taskq)


def run() -> int:
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
