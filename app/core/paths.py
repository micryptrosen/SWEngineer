# File: C:\Dev\CCP\SWEngineer\app\core\paths.py
"""
Project root + path utilities.

Root resolution priority:
1) SWENGINEER_ROOT env var
2) Walk upwards from start path to find a marker file (towershell.ps1)
3) Fallback: two levels above this file
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

PROJECT_ROOT_ENV = "SWENGINEER_ROOT"
ROOT_MARKERS = ("towershell.ps1",)


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def app_dir(self) -> Path:
        return self.root / "app"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def tmp_dir(self) -> Path:
        return self.root / "tmp"

    @property
    def models_dir(self) -> Path:
        return self.root / "data" / "models"

    @property
    def prompts_dir(self) -> Path:
        return self.root / "data" / "prompts"

    @property
    def sessions_dir(self) -> Path:
        return self.root / "data" / "sessions"


DEFAULT_DIRS: tuple[str, ...] = (
    ".vscode",
    "app",
    "app\\core",
    "app\\core\\services",
    "app\\core\\types",
    "app\\engine",
    "app\\engine\\tools",
    "app\\engine\\providers",
    "app\\engine\\runtime",
    "app\\gui",
    "app\\gui\\widgets",
    "app\\gui\\assets",
    "app\\resources",
    "app\\resources\\icons",
    "app\\resources\\themes",
    "data",
    "data\\models",
    "data\\prompts",
    "data\\sessions",
    "data\\telemetry",
    "docs",
    "scripts",
    "tests",
    "tests\\unit",
    "tests\\integration",
    "dist",
    "build",
    "logs",
    "tmp",
)


def resolve_project_root(start: Optional[Path] = None) -> Path:
    env = os.getenv(PROJECT_ROOT_ENV, "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p

    base = (start or Path(__file__)).resolve()
    candidates = [base] + list(base.parents)

    for folder in candidates:
        if folder.is_dir() and any((folder / m).exists() for m in ROOT_MARKERS):
            return folder

    return Path(__file__).resolve().parents[2]


def get_paths(start: Optional[Path] = None) -> ProjectPaths:
    return ProjectPaths(root=resolve_project_root(start))


def ensure_dirs(root: Path, rel_dirs: Iterable[str] = DEFAULT_DIRS) -> None:
    root = root.resolve()
    for rel in rel_dirs:
        (root / rel).mkdir(parents=True, exist_ok=True)


def safe_relpath(root: Path, path: Path) -> str:
    root = root.resolve()
    path = path.resolve()
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def is_probably_text_file(path: Path) -> bool:
    bad_ext = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".exe",
        ".dll",
        ".pdb",
        ".zip",
        ".7z",
        ".rar",
        ".pdf",
    }
    if path.suffix.lower() in bad_ext:
        return False
    try:
        data = path.read_bytes()[:4096]
        if b"\x00" in data:
            return False
        data.decode("utf-8")
        return True
    except Exception:
        return False


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def write_text_atomic(path: Path, content: str) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    tmp.replace(path)
