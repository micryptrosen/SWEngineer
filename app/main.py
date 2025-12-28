# File: C:\Dev\CCP\SWEngineer\app\main.py
"""
LocalAISWE GUI Shell (Windows 11)

Run:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\towershell.ps1 run
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtCore import QDir, QModelIndex, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileSystemModel,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from app.core.paths import get_paths, is_probably_text_file, read_text, safe_relpath, write_text_atomic
from app.engine.engine import Engine, EngineConfig


@dataclass
class FileState:
    path: Optional[Path] = None
    verified_ok: bool = False
    dirty: bool = False


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget, engine: Engine) -> None:
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(520, 160)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.host = QLineEdit(engine.config.ollama_host)
        self.model = QLineEdit(engine.config.ollama_model)

        form.addRow("Ollama host", self.host)
        form.addRow("Ollama model", self.model)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return self.host.text().strip(), self.model.text().strip()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.paths = get_paths()
        self.root = self.paths.root
        self.state = FileState()
        self.engine = Engine()

        self.setWindowTitle("LocalAISWE")
        self.resize(1400, 900)

        self._build_ui()
        self._wire_actions()
        self._refresh_title()
        self._status(f"Project root: {self.root}")

        QTimer.singleShot(50, self._select_app_folder)

    def _build_ui(self) -> None:
        self._build_actions()
        self._build_menu()
        self._build_toolbar()

        outer = QWidget()
        self.setCentralWidget(outer)
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.tree_filter = QLineEdit()
        self.tree_filter.setPlaceholderText("Filter files (type to jump)")
        left_layout.addWidget(self.tree_filter)

        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(str(self.root))
        self.fs_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        self.tree = QTreeView()
        self.tree.setModel(self.fs_model)
        self.tree.setRootIndex(self.fs_model.index(str(self.root)))
        self.tree.setAnimated(True)
        self.tree.setIndentation(14)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        self.tree.setHeaderHidden(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionBehavior(QTreeView.SelectRows)
        self.tree.setUniformRowHeights(True)
        self.tree.setEditTriggers(QTreeView.NoEditTriggers)
        for col in range(1, 4):
            self.tree.hideColumn(col)

        left_layout.addWidget(self.tree, 1)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)

        self.editor_header = QLabel("No file open")
        self.editor_header.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.editor_header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Open a file from the tree (left) or File → Open...")
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(11)
        self.editor.setFont(mono)
        self.editor.setTabStopDistance(self.editor.fontMetrics().horizontalAdvance(" ") * 4)

        center_layout.addWidget(self.editor_header)
        center_layout.addWidget(self.editor, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setPlaceholderText("Assistant messages will appear here.")
        self.chat_log.setMinimumWidth(360)

        input_row = QWidget()
        input_row_layout = QHBoxLayout(input_row)
        input_row_layout.setContentsMargins(0, 0, 0, 0)
        input_row_layout.setSpacing(6)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Message the local engineer")
        self.chat_send = QPushButton("Send")
        self.chat_send.setDefault(True)

        input_row_layout.addWidget(self.chat_input, 1)
        input_row_layout.addWidget(self.chat_send)

        right_layout.addWidget(QLabel("Engineer"))
        right_layout.addWidget(self.chat_log, 1)
        right_layout.addWidget(input_row)

        self.splitter.addWidget(left)
        self.splitter.addWidget(center)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 5)
        self.splitter.setStretchFactor(2, 3)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_actions(self) -> None:
        self.act_open = QAction("Open...", self)
        self.act_open.setShortcut(QKeySequence.Open)

        self.act_save = QAction("Save", self)
        self.act_save.setShortcut(QKeySequence.Save)

        self.act_save_as = QAction("Save As...", self)
        self.act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))

        self.act_close_file = QAction("Close File", self)
        self.act_close_file.setShortcut(QKeySequence.Close)

        self.act_verify = QAction("Verify Current File", self)
        self.act_verify.setShortcut(QKeySequence("Ctrl+Enter"))

        self.act_health = QAction("Ollama Health Check", self)
        self.act_settings = QAction("Settings...", self)

        self.act_run = QAction("Run GUI", self)
        self.act_run.setShortcut(QKeySequence("F5"))

        self.act_quit = QAction("Quit", self)
        self.act_quit.setShortcut(QKeySequence.Quit)

        self.act_reveal = QAction("Reveal in Explorer", self)

    def _build_menu(self) -> None:
        bar = self.menuBar()

        m_file = bar.addMenu("File")
        m_file.addAction(self.act_open)
        m_file.addAction(self.act_save)
        m_file.addAction(self.act_save_as)
        m_file.addSeparator()
        m_file.addAction(self.act_close_file)
        m_file.addSeparator()
        m_file.addAction(self.act_reveal)
        m_file.addSeparator()
        m_file.addAction(self.act_quit)

        m_tools = bar.addMenu("Tools")
        m_tools.addAction(self.act_verify)
        m_tools.addSeparator()
        m_tools.addAction(self.act_health)
        m_tools.addAction(self.act_settings)
        m_tools.addSeparator()
        m_tools.addAction(self.act_run)

        m_help = QMenu("Help", self)
        bar.addMenu(m_help)
        about = QAction("About", self)
        about.triggered.connect(self._about)
        m_help.addAction(about)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addAction(self.act_open)
        tb.addAction(self.act_save)
        tb.addAction(self.act_verify)

    def _wire_actions(self) -> None:
        self.act_open.triggered.connect(self._open_dialog)
        self.act_save.triggered.connect(self._save)
        self.act_save_as.triggered.connect(self._save_as)
        self.act_close_file.triggered.connect(self._close_file)
        self.act_verify.triggered.connect(self._verify_current)
        self.act_quit.triggered.connect(self.close)
        self.act_reveal.triggered.connect(self._reveal_in_explorer)
        self.act_run.triggered.connect(self._run_gui_again)
        self.act_health.triggered.connect(self._ollama_health_check)
        self.act_settings.triggered.connect(self._open_settings)

        self.tree.doubleClicked.connect(self._tree_open)
        self.tree_filter.textChanged.connect(self._tree_jump)

        self.editor.textChanged.connect(self._on_editor_changed)

        self.chat_send.clicked.connect(self._chat_send)
        self.chat_input.returnPressed.connect(self._chat_send)

    def _status(self, text: str) -> None:
        self.status_bar.showMessage(text, 6000)

    def _refresh_title(self) -> None:
        name = "LocalAISWE"
        if self.state.path:
            rel = safe_relpath(self.root, self.state.path)
            flags: list[str] = []
            if self.state.dirty:
                flags.append("modified")
            if self.state.verified_ok:
                flags.append("verified")
            suffix = f" — {rel}"
            if flags:
                suffix += f" ({', '.join(flags)})"
            self.setWindowTitle(name + suffix)
        else:
            self.setWindowTitle(name)

        self.editor_header.setText(str(self.state.path) if self.state.path else "No file open")

    def _select_app_folder(self) -> None:
        idx = self.fs_model.index(str(self.root / "app"))
        if idx.isValid():
            self.tree.expand(idx)
            self.tree.setCurrentIndex(idx)

    def _tree_jump(self, text: str) -> None:
        text = text.strip()
        if text:
            self.tree.keyboardSearch(text)

    def _guard_switch_file(self) -> bool:
        if not self.state.path or not self.state.dirty:
            return True

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Unverified changes")
        msg.setText("Current file has unverified changes.")
        msg.setInformativeText("Verify or discard changes before opening another file.")
        btn_verify = msg.addButton("Verify", QMessageBox.AcceptRole)
        btn_discard = msg.addButton("Discard Changes", QMessageBox.DestructiveRole)
        msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_verify:
            return self._verify_current()
        if msg.clickedButton() == btn_discard:
            self._reload_current_from_disk()
            return True
        return False

    def _tree_open(self, index: QModelIndex) -> None:
        if index.isValid():
            path = Path(self.fs_model.filePath(index))
            if path.is_file():
                self._open_file(path)

    def _open_dialog(self) -> None:
        if not self._guard_switch_file():
            return
        p, _ = QFileDialog.getOpenFileName(self, "Open File", str(self.root), "All Files (*.*)")
        if p:
            self._open_file(Path(p))

    def _open_file(self, path: Path) -> None:
        if not self._guard_switch_file():
            return

        path = path.resolve()
        if not path.exists():
            QMessageBox.critical(self, "Open failed", f"File not found:\n{path}")
            return
        if not is_probably_text_file(path):
            QMessageBox.warning(self, "Unsupported", f"Not a supported text file:\n{path}")
            return

        self.editor.blockSignals(True)
        self.editor.setPlainText(read_text(path))
        self.editor.blockSignals(False)

        self.state = FileState(path=path, verified_ok=False, dirty=False)
        self._refresh_title()
        self._status(f"Opened: {path}")

    def _reload_current_from_disk(self) -> None:
        if not self.state.path:
            return
        self.editor.blockSignals(True)
        self.editor.setPlainText(read_text(self.state.path))
        self.editor.blockSignals(False)
        self.state.dirty = False
        self.state.verified_ok = False
        self._refresh_title()

    def _on_editor_changed(self) -> None:
        if self.state.path:
            self.state.dirty = True
            self.state.verified_ok = False
            self._refresh_title()

    def _save(self) -> bool:
        if not self.state.path:
            return self._save_as()
        try:
            write_text_atomic(self.state.path, self.editor.toPlainText())
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"{self.state.path}\n\n{e}")
            return False
        self.state.dirty = False
        self._refresh_title()
        self._status("Saved")
        return True

    def _save_as(self) -> bool:
        p, _ = QFileDialog.getSaveFileName(self, "Save As", str(self.root), "All Files (*.*)")
        if not p:
            return False
        self.state.path = Path(p).resolve()
        ok = self._save()
        self._refresh_title()
        return ok

    def _close_file(self) -> None:
        if self.state.dirty:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Unsaved changes")
            msg.setText("Save changes before closing?")
            btn_save = msg.addButton("Save", QMessageBox.AcceptRole)
            btn_discard = msg.addButton("Discard", QMessageBox.DestructiveRole)
            msg.addButton("Cancel", QMessageBox.RejectRole)
            msg.exec()

            if msg.clickedButton() == btn_save:
                if not self._save():
                    return
            elif msg.clickedButton() == btn_discard:
                pass
            else:
                return

        self.editor.blockSignals(True)
        self.editor.setPlainText("")
        self.editor.blockSignals(False)
        self.state = FileState()
        self._refresh_title()
        self._status("Closed file")

    def _verify_current(self) -> bool:
        if not self.state.path:
            QMessageBox.information(self, "Verify", "No file open.")
            return False

        if self.state.dirty and not self._save():
            return False

        ts = (self.root / "towershell.ps1").resolve()
        if not ts.exists():
            QMessageBox.critical(self, "Verify failed", f"Missing towershell:\n{ts}")
            return False

        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ts),
            "verify",
            str(self.state.path),
        ]
        proc = subprocess.run(cmd, cwd=str(self.root), capture_output=True, text=True)
        if proc.returncode != 0:
            self.state.verified_ok = False
            self._refresh_title()
            QMessageBox.critical(self, "Verify failed", (proc.stdout + "\n" + proc.stderr).strip() or "Unknown error")
            return False

        self.state.verified_ok = True
        self._refresh_title()
        self._status("Verified OK")
        return True

    def _ollama_health_check(self) -> None:
        ok, info = self.engine.health()
        title = "Ollama Health Check"
        if ok:
            QMessageBox.information(
                self,
                title,
                f"OK\n\nHost: {self.engine.config.ollama_host}\nModel: {self.engine.config.ollama_model}",
            )
        else:
            QMessageBox.critical(
                self,
                title,
                f"FAILED\n\nHost: {self.engine.config.ollama_host}\nModel: {self.engine.config.ollama_model}\n\n{info}",
            )

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self, self.engine)
        if dlg.exec() != QDialog.Accepted:
            return

        host, model = dlg.values()
        if not host or not model:
            QMessageBox.warning(self, "Settings", "Host and model are required.")
            return

        os.environ["OLLAMA_HOST"] = host
        os.environ["OLLAMA_MODEL"] = model

        self.engine = Engine(EngineConfig(ollama_host=host, ollama_model=model, system_prompt=self.engine.config.system_prompt))
        self.chat_log.append(f"<i>Settings updated: host={host}, model={model}</i>")

    def _reveal_in_explorer(self) -> None:
        target = self.state.path if self.state.path else self.root
        try:
            if target.is_file():
                subprocess.run(["explorer", "/select,", str(target)], check=False)
            else:
                subprocess.run(["explorer", str(target)], check=False)
        except Exception:
            pass

    def _run_gui_again(self) -> None:
        ts = (self.root / "towershell.ps1").resolve()
        if ts.exists():
            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ts), "run"],
                cwd=str(self.root),
                creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
            )

    def _chat_send(self) -> None:
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        self.chat_log.append(f"<b>You:</b> {text}")

        try:
            reply = self.engine.send_user(text)
        except Exception as e:
            self.chat_log.append(f"<b>Engineer:</b> ERROR: {e}")
            return

        self.chat_log.append(f"<b>Engineer:</b> {reply or '(no response)'}")

    def _about(self) -> None:
        QMessageBox.information(self, "About", "LocalAISWE\n\nGUI + Engine (Ollama provider).")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.state.dirty:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Unsaved changes")
            msg.setText("Save changes before quitting?")
            btn_save = msg.addButton("Save", QMessageBox.AcceptRole)
            btn_discard = msg.addButton("Discard", QMessageBox.DestructiveRole)
            msg.addButton("Cancel", QMessageBox.RejectRole)
            msg.exec()

            if msg.clickedButton() == btn_save:
                if not self._save():
                    event.ignore()
                    return
            elif msg.clickedButton() == btn_discard:
                pass
            else:
                event.ignore()
                return
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
