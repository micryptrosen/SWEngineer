# --- Phase1D: optional flow spine wiring (no behavior change by default) ---


# Set SWENGINEER_FLOW_SPINE=1 to route through the internal spine surface.


def _phase1d_try_flow_spine() -> bool:


    try:


        import os


        if os.environ.get("SWENGINEER_FLOW_SPINE", "").strip() != "1":


            return False


        from swe_runner.flow_spine import run_flow


        # Minimal intent; Phase1E will pass real intent inputs.


        res = run_flow({"source": "app.main", "phase": "1D"})


        # Do not print unless explicitly requested (keep behavior unchanged).


        _ = res


        return True


    except Exception:


        # Silent by design for Phase1D.


        return False


# --- end Phase1D wiring ---





# File: C:\Dev\CCP\SWEngineer\app\main.py


from __future__ import annotations


from pathlib import Path as _Path


import sys as _sys





def _swe_find_repo_root(_start: _Path) -> _Path:


    p = _start.resolve()


    for _ in range(8):


        if (p / 'src').exists() and (p / 'vendor').exists():


            return p


        if p.parent == p:


            break


        p = p.parent


    return _start.resolve().parents[0]





_REPO = _swe_find_repo_root(_Path(__file__).resolve())


_SRC = _REPO / 'src'


_VENDOR = _REPO / 'vendor' / 'swe-schemas'


for _p in (str(_VENDOR), str(_SRC)):


    if _p and _p not in _sys.path:


        _sys.path.insert(0, _p)





import swe_bootstrap as _swe_bootstrap


_swe_bootstrap.apply()











import difflib


import os


import subprocess


import sys


from dataclasses import dataclass


from datetime import datetime


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


    QInputDialog,


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





from app.core.config import AppConfig, load_config, save_config


from app.core.paths import (


    get_paths,


    is_probably_text_file,


    read_text,


    safe_relpath,


    write_text_atomic,


)


from app.engine.actions import (


    FileBlock,


    extract_file_blocks_from_markdown,


    parse_engineer_payload,


    payload_to_file_blocks,


)


from app.engine.engine import Engine, EngineConfig





# ---- Policy switches (your selections) ----


APPLY_ROOT_ONLY = True


APPLY_ALLOW_DOTDOT = True  # A2=N -> allow ".." as long as it resolves under root


APPLY_ALLOW_CREATE = True  # A3=Y


APPLY_BACKUP_BAK = True  # A5=Y (timestamped)


APPLY_MAX_BYTES = 2 * 1024 * 1024  # A6=2MB


APPLY_MAX_LINES = 20_000  # A6=20k


APPLY_REQUIRE_TYPE_YES = False  # B4=N


APPLY_SHOW_TARGET_STATS = True  # B5=Y


APPLY_DIFF_PREVIEW = True


APPLY_COPY_DIFF_BUTTON = True


APPLY_BLOCK_OVERWRITE_UNLESS_OPEN = True


APPLY_AUTO_VERIFY = True


APPLY_AUTO_OPEN = True


LOCK_ONE_FILE_AT_A_TIME = True  # D3=Y


REFUSE_APPLY_IF_CURRENT_DIRTY = True  # D4=Y


ENGINE_JSON_ONLY_EXPECTED = True  # E1=Y


ENGINE_STRICT_ACTION_WHITELIST = True  # E2=Y


ENGINE_REFUSE_MISSING_PATH = True  # E3=Y


ENGINE_ALLOW_LEGACY_FALLBACK = True  # E4=Y


APPLY_LOG_ENABLED = True  # F1=Y


CHAT_HISTORY_MAX = 50  # F2=Y(50)





_ALLOWED_ACTION_TYPES = {"file_write", "verify", "open", "message"}





_BINARY_EXTS = {


    ".png",


    ".jpg",


    ".jpeg",


    ".gif",


    ".webp",


    ".bmp",


    ".ico",


    ".pdf",


    ".zip",


    ".7z",


    ".rar",


    ".gz",


    ".tar",


    ".whl",


    ".exe",


    ".dll",


    ".pyd",


    ".so",


    ".dylib",


    ".bin",


    ".dat",


}








def _is_probably_text_content(content: str) -> bool:


    if "\x00" in content:


        return False


    sample = content[:4096]


    if not sample:


        return True


    bad = 0


    total = len(sample)


    for ch in sample:


        o = ord(ch)


        if ch in ("\n", "\r", "\t"):


            continue


        if 32 <= o <= 126:


            continue


        if o >= 160:


            continue


        bad += 1


    return (bad / total) <= 0.02








@dataclass


class FileState:


    path: Optional[Path] = None


    dirty: bool = False


    verified_ok: bool = False








class SettingsDialog(QDialog):


    def __init__(self, parent: QWidget, cfg: AppConfig) -> None:


        super().__init__(parent)


        self.setWindowTitle("Settings")


        self.setModal(True)


        self.resize(520, 160)





        layout = QVBoxLayout(self)


        form = QFormLayout()


        layout.addLayout(form)





        self.host = QLineEdit(cfg.ollama_host)


        self.model = QLineEdit(cfg.ollama_model)





        form.addRow("Ollama host", self.host)


        form.addRow("Ollama model", self.model)





        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)


        buttons.accepted.connect(self.accept)


        buttons.rejected.connect(self.reject)


        layout.addWidget(buttons)





    def values(self) -> AppConfig:


        return AppConfig(


            ollama_host=self.host.text().strip(),


            ollama_model=self.model.text().strip(),


        )








class ApplyConfirmDialog(QDialog):


    def __init__(


        self,


        parent: QWidget,


        *,


        target_rel: str,


        line_count: int,


        byte_count: int,


        exists: bool,


        diff_text: str,


        require_type_yes: bool,


    ) -> None:


        super().__init__(parent)


        self.setModal(True)


        self.setWindowTitle("Confirm Apply")


        self.resize(1000, 720)





        layout = QVBoxLayout(self)





        mode = "OVERWRITE" if exists else "CREATE"


        header_bits = [


            f"<b>Target</b>: {target_rel}",


            f"<b>Lines</b>: {line_count}",


            f"<b>Bytes</b>: {byte_count}",


            f"<b>Mode</b>: {mode}",


        ]


        header = QLabel("<br>".join(header_bits))


        header.setTextInteractionFlags(Qt.TextSelectableByMouse)


        layout.addWidget(header)





        self.diff_view = QPlainTextEdit()


        self.diff_view.setReadOnly(True)


        mono = QFont("Consolas")


        mono.setStyleHint(QFont.Monospace)


        mono.setPointSize(10)


        self.diff_view.setFont(mono)


        self.diff_view.setPlainText(diff_text)


        layout.addWidget(self.diff_view, 1)





        footer = QWidget()


        footer_l = QHBoxLayout(footer)


        footer_l.setContentsMargins(0, 0, 0, 0)


        footer_l.setSpacing(8)





        self.btn_copy = QPushButton("Copy Diff")


        self.btn_copy.clicked.connect(self._copy_diff)


        self.btn_copy.setEnabled(APPLY_COPY_DIFF_BUTTON)





        self.type_yes = QLineEdit()


        if require_type_yes:


            self.type_yes.setPlaceholderText("Type YES to enable Proceed")


            self.type_yes.textChanged.connect(self._on_type_changed)


        self.type_yes.setVisible(require_type_yes)





        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)


        self.buttons.button(QDialogButtonBox.Ok).setText("Proceed")


        self.buttons.button(QDialogButtonBox.Ok).setEnabled(not require_type_yes)


        self.buttons.accepted.connect(self.accept)


        self.buttons.rejected.connect(self.reject)





        footer_l.addWidget(self.btn_copy)


        if require_type_yes:


            footer_l.addWidget(self.type_yes, 1)


        else:


            footer_l.addStretch(1)


        footer_l.addWidget(self.buttons)


        layout.addWidget(footer)





    def _copy_diff(self) -> None:


        QApplication.clipboard().setText(self.diff_view.toPlainText())


        QMessageBox.information(self, "Copied", "Diff copied to clipboard.")





    def _on_type_changed(self, text: str) -> None:


        ok_btn = self.buttons.button(QDialogButtonBox.Ok)


        ok_btn.setEnabled(text.strip().upper() == "YES")








class MainWindow(QMainWindow):


    def __init__(self) -> None:


        super().__init__()





        self.paths = get_paths()


        self.root: Path = self.paths.root.resolve()


        self.state = FileState()





        self.cfg = load_config(self.root)


        save_config(self.root, self.cfg)





        self.engine = Engine(


            EngineConfig(


                ollama_host=self.cfg.ollama_host,


                ollama_model=self.cfg.ollama_model,


            )


        )





        self._chat: list[tuple[str, str]] = []





        self.setWindowTitle("LocalAISWE")


        self.resize(1400, 900)





        self._build_ui()


        self._wire()


        self._refresh_title()


        self._status(f"Root: {self.root}")





        QTimer.singleShot(30, self._select_app_folder)





    # ---------- UI ----------





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


        left_l = QVBoxLayout(left)


        left_l.setContentsMargins(0, 0, 0, 0)


        left_l.setSpacing(6)





        self.tree_filter = QLineEdit()


        self.tree_filter.setPlaceholderText("Type to jump")


        left_l.addWidget(self.tree_filter)





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


        self.tree.setSelectionBehavior(QTreeView.SelectRows)


        self.tree.setUniformRowHeights(True)


        self.tree.setEditTriggers(QTreeView.NoEditTriggers)


        for col in range(1, 4):


            self.tree.hideColumn(col)





        left_l.addWidget(self.tree, 1)





        center = QWidget()


        center_l = QVBoxLayout(center)


        center_l.setContentsMargins(0, 0, 0, 0)


        center_l.setSpacing(6)





        self.editor_header = QLabel("No file open")


        self.editor_header.setTextInteractionFlags(Qt.TextSelectableByMouse)


        self.editor_header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)





        self.editor = QPlainTextEdit()


        self.editor.setPlaceholderText("Open a file to edit")


        mono = QFont("Consolas")


        mono.setStyleHint(QFont.Monospace)


        mono.setPointSize(11)


        self.editor.setFont(mono)


        self.editor.setTabStopDistance(self.editor.fontMetrics().horizontalAdvance(" ") * 4)





        center_l.addWidget(self.editor_header)


        center_l.addWidget(self.editor, 1)





        right = QWidget()


        right_l = QVBoxLayout(right)


        right_l.setContentsMargins(0, 0, 0, 0)


        right_l.setSpacing(6)





        right_l.addWidget(QLabel("Engineer"))





        self.chat_log = QTextEdit()


        self.chat_log.setReadOnly(True)


        self.chat_log.setMinimumWidth(360)


        right_l.addWidget(self.chat_log, 1)





        row = QWidget()


        row_l = QHBoxLayout(row)


        row_l.setContentsMargins(0, 0, 0, 0)


        row_l.setSpacing(6)





        self.chat_input = QLineEdit()


        self.chat_input.setPlaceholderText("Message")


        self.chat_send = QPushButton("Send")


        self.chat_send.setDefault(True)





        row_l.addWidget(self.chat_input, 1)


        row_l.addWidget(self.chat_send)





        right_l.addWidget(row)





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





        self.act_close = QAction("Close File", self)


        self.act_close.setShortcut(QKeySequence.Close)





        self.act_verify = QAction("Verify Current File", self)


        self.act_verify.setShortcut(QKeySequence("Ctrl+Enter"))





        self.act_apply_last = QAction("Apply from Last Engineer (JSON/actions)", self)


        self.act_apply_last.setShortcut(QKeySequence("Ctrl+Shift+Enter"))





        self.act_settings = QAction("Settings...", self)


        self.act_health = QAction("Ollama Health Check", self)





        self.act_reveal = QAction("Reveal in Explorer", self)


        self.act_quit = QAction("Quit", self)


        self.act_quit.setShortcut(QKeySequence.Quit)





        self.act_run = QAction("Run GUI", self)


        self.act_run.setShortcut(QKeySequence("F5"))





    def _build_menu(self) -> None:


        bar = self.menuBar()





        m_file = bar.addMenu("File")


        m_file.addAction(self.act_open)


        m_file.addAction(self.act_save)


        m_file.addAction(self.act_save_as)


        m_file.addSeparator()


        m_file.addAction(self.act_close)


        m_file.addSeparator()


        m_file.addAction(self.act_reveal)


        m_file.addSeparator()


        m_file.addAction(self.act_quit)





        m_tools = bar.addMenu("Tools")


        m_tools.addAction(self.act_verify)


        m_tools.addAction(self.act_apply_last)


        m_tools.addSeparator()


        m_tools.addAction(self.act_health)


        m_tools.addAction(self.act_settings)


        m_tools.addSeparator()


        m_tools.addAction(self.act_run)





        m_help = QMenu("Help", self)


        bar.addMenu(m_help)


        about = QAction("About", self)


        about.triggered.connect(lambda: QMessageBox.information(self, "About", "LocalAISWE"))


        m_help.addAction(about)





    def _build_toolbar(self) -> None:


        tb = QToolBar("Main")


        tb.setMovable(False)


        self.addToolBar(tb)


        tb.addAction(self.act_open)


        tb.addAction(self.act_save)


        tb.addAction(self.act_verify)


        tb.addAction(self.act_apply_last)





    def _wire(self) -> None:


        self.act_open.triggered.connect(self._open_dialog)


        self.act_save.triggered.connect(self._save)


        self.act_save_as.triggered.connect(self._save_as)


        self.act_close.triggered.connect(self._close_file)


        self.act_verify.triggered.connect(self._verify_current)


        self.act_apply_last.triggered.connect(self._apply_from_last_engineer)


        self.act_settings.triggered.connect(self._open_settings)


        self.act_health.triggered.connect(self._health)


        self.act_reveal.triggered.connect(self._reveal)


        self.act_quit.triggered.connect(self.close)


        self.act_run.triggered.connect(self._run_gui_again)





        self.tree.doubleClicked.connect(self._tree_open)


        self.tree_filter.textChanged.connect(


            lambda t: self.tree.keyboardSearch(t.strip()) if t.strip() else None


        )





        self.editor.textChanged.connect(self._on_editor_changed)


        self.chat_send.clicked.connect(self._chat_send)


        self.chat_input.returnPressed.connect(self._chat_send)





    # ---------- helpers ----------





    def _status(self, text: str) -> None:


        self.status_bar.showMessage(text, 6000)





    def _refresh_title(self) -> None:


        if self.state.path:


            rel = safe_relpath(self.root, self.state.path)


            flags: list[str] = []


            if self.state.dirty:


                flags.append("modified")


            if self.state.verified_ok:


                flags.append("verified")


            else:


                flags.append("unverified")


            self.setWindowTitle(f"LocalAISWE — {rel} ({', '.join(flags)})")


            self.editor_header.setText(str(self.state.path))


        else:


            self.setWindowTitle("LocalAISWE")


            self.editor_header.setText("No file open")





    def _select_app_folder(self) -> None:


        idx = self.fs_model.index(str(self.root / "app"))


        if idx.isValid():


            self.tree.expand(idx)


            self.tree.setCurrentIndex(idx)





    def _resolve_under_root(self, p: Path) -> Optional[Path]:


        try:


            rp = p.resolve()


        except Exception:


            return None


        if APPLY_ROOT_ONLY:


            try:


                rp.relative_to(self.root)


            except Exception:


                return None


        return rp





    def _append_apply_log(self, action: str, target: Path, exists: bool, content: str) -> None:


        if not APPLY_LOG_ENABLED:


            return


        try:


            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


            rel = safe_relpath(self.root, target)


            mode = "OVERWRITE" if exists else "CREATE"


            lines = len((content or "").splitlines())


            bytes_ = len((content or "").encode("utf-8", errors="replace"))


            self.paths.data.mkdir(parents=True, exist_ok=True)


            log_path = self.paths.data / "apply.log"


            with log_path.open("a", encoding="utf-8") as f:


                f.write(f"{ts}\t{action}\t{mode}\t{rel}\tlines={lines}\tbytes={bytes_}\n")


        except Exception:


            pass





    def _enforce_one_file_lock(self) -> bool:


        if not LOCK_ONE_FILE_AT_A_TIME:


            return True


        if not self.state.path:


            return True


        if self.state.dirty or not self.state.verified_ok:


            msg = QMessageBox(self)


            msg.setIcon(QMessageBox.Warning)


            msg.setWindowTitle("One file at a time")


            msg.setText("Current file must be verified before switching.")


            btn_verify = msg.addButton("Verify", QMessageBox.AcceptRole)


            msg.addButton("Cancel", QMessageBox.RejectRole)


            msg.exec()


            if msg.clickedButton() == btn_verify:


                return self._verify_current()


            return False


        return True





    def _guard_switch_file(self) -> bool:


        if not self._enforce_one_file_lock():


            return False





        if not self.state.path or not self.state.dirty:


            return True





        msg = QMessageBox(self)


        msg.setIcon(QMessageBox.Warning)


        msg.setWindowTitle("Unsaved changes")


        msg.setText("Current file has unsaved changes.")


        btn_save = msg.addButton("Save", QMessageBox.AcceptRole)


        msg.addButton("Cancel", QMessageBox.RejectRole)


        msg.exec()





        if msg.clickedButton() == btn_save:


            return self._save() and self._verify_current()


        return False





    def _on_editor_changed(self) -> None:


        if self.state.path:


            self.state.dirty = True


            self.state.verified_ok = False


            self._refresh_title()





    def _make_unified_diff(self, before: str, after: str, *, rel: str, exists: bool) -> str:


        a_name = f"{rel} (current)" if exists else f"{rel} (new-file: empty)"


        b_name = f"{rel} (incoming)"


        a_lines = (before or "").splitlines(keepends=True)


        b_lines = (after or "").splitlines(keepends=True)


        diff = difflib.unified_diff(a_lines, b_lines, fromfile=a_name, tofile=b_name, n=3)


        out = "".join(diff)


        if not out.strip():


            return "(No diff) Incoming content is identical to current content.\n"


        return out





    def _block_if_binary_target(self, target: Path, incoming: str) -> bool:


        if target.suffix.lower() in _BINARY_EXTS:


            QMessageBox.critical(


                self, "Apply blocked", f"Refusing binary extension:\n{target.name}"


            )


            return True


        if target.exists() and not is_probably_text_file(target):


            QMessageBox.critical(


                self, "Apply blocked", f"Refusing to overwrite non-text file:\n{target.name}"


            )


            return True


        if not _is_probably_text_content(incoming):


            QMessageBox.critical(self, "Apply blocked", "Incoming content looks non-text/binary.")


            return True


        return False





    def _block_if_too_large(self, incoming: str) -> bool:


        lines = len((incoming or "").splitlines())


        if APPLY_MAX_LINES and lines > APPLY_MAX_LINES:


            QMessageBox.critical(


                self,


                "Apply blocked",


                f"Incoming content too many lines: {lines} > {APPLY_MAX_LINES}",


            )


            return True


        if APPLY_MAX_BYTES:


            b = len((incoming or "").encode("utf-8", errors="replace"))


            if b > APPLY_MAX_BYTES:


                QMessageBox.critical(


                    self,


                    "Apply blocked",


                    f"Incoming content too large: {b} bytes > {APPLY_MAX_BYTES} bytes",


                )


                return True


        return False





    def _confirm_apply(self, target: Path, incoming: str, exists: bool) -> bool:


        rel = safe_relpath(self.root, target)


        before = read_text(target) if exists else ""


        diff_text = self._make_unified_diff(before, incoming, rel=rel, exists=exists)


        line_count = len((incoming or "").splitlines())


        byte_count = len((incoming or "").encode("utf-8", errors="replace"))


        dlg = ApplyConfirmDialog(


            self,


            target_rel=rel,


            line_count=line_count,


            byte_count=byte_count,


            exists=exists,


            diff_text=diff_text,


            require_type_yes=APPLY_REQUIRE_TYPE_YES,


        )


        return dlg.exec() == QDialog.Accepted





    def _backup_before_overwrite(self, target: Path) -> None:


        if not APPLY_BACKUP_BAK or not target.exists():


            return


        ts = datetime.now().strftime("%Y%m%d-%H%M%S")


        bak = target.with_name(f"{target.name}.bak.{ts}")


        try:


            bak.write_text(read_text(target), encoding="utf-8")


        except Exception:


            pass





    def _parse_engine_reply_to_blocks(self, text: str) -> Optional[list[FileBlock]]:


        text = text or ""





        payload = parse_engineer_payload(text)


        if payload:


            if ENGINE_STRICT_ACTION_WHITELIST:


                for a in payload.actions:


                    if a.type not in _ALLOWED_ACTION_TYPES:


                        QMessageBox.critical(


                            self, "Apply blocked", f"Disallowed action type: {a.type}"


                        )


                        return None


            blocks = payload_to_file_blocks(payload)


            if ENGINE_REFUSE_MISSING_PATH:


                for b in blocks:


                    if not (b.path and b.path.strip()):


                        QMessageBox.critical(self, "Apply blocked", "file_write missing path.")


                        return None


            return blocks





        if ENGINE_JSON_ONLY_EXPECTED and not ENGINE_ALLOW_LEGACY_FALLBACK:


            QMessageBox.critical(self, "Apply blocked", "Engineer reply is not valid JSON.")


            return None





        if ENGINE_ALLOW_LEGACY_FALLBACK:


            blocks = extract_file_blocks_from_markdown(text)


            return blocks or None





        return None





    # ---------- file operations ----------





    def _tree_open(self, index: QModelIndex) -> None:


        if not index.isValid():


            return


        p = Path(self.fs_model.filePath(index))


        if p.is_file():


            self._open_file(p)





    def _open_dialog(self) -> None:


        if not self._guard_switch_file():


            return


        p, _ = QFileDialog.getOpenFileName(self, "Open File", str(self.root), "All Files (*.*)")


        if p:


            self._open_file(Path(p))





    def _open_file(self, path: Path) -> None:


        if not self._guard_switch_file():


            return





        rp = self._resolve_under_root(path)


        if rp is None or not rp.exists():


            QMessageBox.critical(self, "Open failed", f"Not under project root:\n{path}")


            return


        if not is_probably_text_file(rp):


            QMessageBox.warning(self, "Unsupported", f"Not a supported text file:\n{rp}")


            return





        self.editor.blockSignals(True)


        self.editor.setPlainText(read_text(rp))


        self.editor.blockSignals(False)





        self.state = FileState(path=rp, dirty=False, verified_ok=False)


        self._refresh_title()


        self._status(f"Opened: {rp}")





    def _reload_current(self) -> None:


        if not self.state.path:


            return


        self.editor.blockSignals(True)


        self.editor.setPlainText(read_text(self.state.path))


        self.editor.blockSignals(False)


        self.state.dirty = False


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


        rp = self._resolve_under_root(Path(p))


        if rp is None:


            QMessageBox.critical(self, "Save As", "Target must be under project root.")


            return False


        self.state.path = rp


        return self._save()





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





    def _verify_current(self) -> bool:


        if not self.state.path:


            QMessageBox.information(self, "Verify", "No file open.")


            return False


        if self.state.dirty and not self._save():


            return False





        ts = (self.root / "towershell.ps1").resolve()


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


            QMessageBox.critical(


                self, "Verify failed", (proc.stdout + "\n" + proc.stderr).strip() or "Unknown error"


            )


            return False





        self.state.verified_ok = True


        self._refresh_title()


        self._status("Verified OK")


        return True





    # ---------- tools ----------





    def _open_settings(self) -> None:


        dlg = SettingsDialog(self, self.cfg)


        if dlg.exec() != QDialog.Accepted:


            return


        cfg = dlg.values()


        if not cfg.ollama_host or not cfg.ollama_model:


            QMessageBox.warning(self, "Settings", "Host and model are required.")


            return





        self.cfg = cfg


        save_config(self.root, self.cfg)





        os.environ["OLLAMA_HOST"] = cfg.ollama_host


        os.environ["OLLAMA_MODEL"] = cfg.ollama_model





        self.engine = Engine(


            EngineConfig(ollama_host=cfg.ollama_host, ollama_model=cfg.ollama_model)


        )


        self._append_chat(


            "System", f"Saved settings: host={cfg.ollama_host}, model={cfg.ollama_model}"


        )





    def _health(self) -> None:


        ok, info = self.engine.health()


        if ok:


            QMessageBox.information(self, "Ollama Health", "OK")


        else:


            QMessageBox.critical(self, "Ollama Health", f"FAILED\n\n{info}")





    def _reveal(self) -> None:


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


                creationflags=(


                    subprocess.CREATE_NEW_CONSOLE


                    if hasattr(subprocess, "CREATE_NEW_CONSOLE")


                    else 0


                ),


            )





    # ---------- chat / apply ----------





    def _append_chat(self, who: str, msg: str) -> None:


        self._chat.append((who, msg))


        if len(self._chat) > CHAT_HISTORY_MAX:


            self._chat = self._chat[-CHAT_HISTORY_MAX:]


        self.chat_log.append(f"<b>{who}:</b> {msg}")





    def _chat_send(self) -> None:


        text = self.chat_input.text().strip()


        if not text:


            return


        self.chat_input.clear()


        self._append_chat("You", text)





        try:


            reply = self.engine.send_user(text)


        except Exception as e:


            self._append_chat("Engineer", f"ERROR: {e}")


            return





        payload = parse_engineer_payload(reply or "")


        if payload and payload.final_message:


            self._append_chat("Engineer", payload.final_message)


            self._append_chat("EngineerRaw", reply or "")


        else:


            self._append_chat("Engineer", (reply or "").strip() or "(no response)")





    def _latest_engineer_raw(self) -> str:


        for who, msg in reversed(self._chat):


            if who == "EngineerRaw":


                return msg


        for who, msg in reversed(self._chat):


            if who == "Engineer":


                return msg


        return ""





    def _choose_block(self, blocks: list[FileBlock]) -> Optional[FileBlock]:


        if not blocks:


            return None


        if len(blocks) == 1:


            return blocks[0]


        choices = [b.path for b in blocks]


        choice, ok = QInputDialog.getItem(self, "Apply", "Choose file:", choices, 0, False)


        if not ok or not choice:


            return None


        for b in blocks:


            if b.path == choice:


                return b


        return None





    def _apply_from_last_engineer(self) -> None:


        if REFUSE_APPLY_IF_CURRENT_DIRTY and self.state.path and self.state.dirty:


            QMessageBox.critical(


                self,


                "Apply blocked",


                "Current file is dirty.\n\nSave + verify the current file before applying.",


            )


            return





        text = self._latest_engineer_raw()


        if not text.strip():


            QMessageBox.information(self, "Apply", "No Engineer message found.")


            return





        blocks = self._parse_engine_reply_to_blocks(text)


        if not blocks:


            QMessageBox.information(self, "Apply", "No applicable file_write found.")


            return





        chosen = self._choose_block(blocks)


        if not chosen:


            return





        if ENGINE_REFUSE_MISSING_PATH and not (chosen.path and chosen.path.strip()):


            QMessageBox.critical(self, "Apply blocked", "Missing target path.")


            return





        target = Path(chosen.path.strip())


        if not target.is_absolute():


            target = self.root / target





        target = self._resolve_under_root(target)


        if target is None:


            QMessageBox.critical(self, "Apply blocked", "Target path must be under project root.")


            return





        exists = target.exists()





        if exists and APPLY_BLOCK_OVERWRITE_UNLESS_OPEN:


            opened = self.state.path.resolve() if self.state.path else None


            if opened is None or opened != target:


                QMessageBox.critical(


                    self,


                    "Apply blocked",


                    "Refusing to overwrite.\n\nOpen the target file in the editor first, then Apply again.",


                )


                return





        if not exists and not APPLY_ALLOW_CREATE:


            QMessageBox.critical(


                self, "Apply blocked", "Target does not exist and creation is disabled."


            )


            return





        if self._block_if_binary_target(target, chosen.content):


            return


        if self._block_if_too_large(chosen.content):


            return





        if not self._confirm_apply(target, chosen.content, exists):


            return





        if exists:


            self._backup_before_overwrite(target)





        try:


            target.parent.mkdir(parents=True, exist_ok=True)


            write_text_atomic(target, chosen.content)


        except Exception as e:


            QMessageBox.critical(self, "Apply failed", f"{target}\n\n{e}")


            return





        self._append_apply_log("file_write", target, exists, chosen.content)





        if APPLY_AUTO_OPEN:


            if exists and self.state.path and self.state.path.resolve() == target:


                self._reload_current()


            else:


                self._open_file(target)





        if APPLY_AUTO_VERIFY:


            self._verify_current()





    # ---------- close ----------





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


    if _phase1d_try_flow_spine():
        return 0
    app = QApplication(sys.argv)


    w = MainWindow()


    w.show()


    return app.exec()








if __name__ == "__main__":


    raise SystemExit(main())



