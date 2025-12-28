# File: C:\Dev\CCP\SWEngineer\app\core\config.py
"""
App config persistence (data/config.json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    @staticmethod
    def from_dict(d: dict) -> "AppConfig":
        return AppConfig(
            ollama_host=str(d.get("ollama_host") or AppConfig.ollama_host),
            ollama_model=str(d.get("ollama_model") or AppConfig.ollama_model),
        )

    def to_dict(self) -> dict:
        return {"ollama_host": self.ollama_host, "ollama_model": self.ollama_model}


def config_path(project_root: Path) -> Path:
    return project_root / "data" / "config.json"


def load_config(project_root: Path) -> AppConfig:
    p = config_path(project_root)
    if not p.exists():
        return AppConfig()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return AppConfig.from_dict(data)
        return AppConfig()
    except Exception:
        return AppConfig()


def save_config(project_root: Path, cfg: AppConfig) -> None:
    p = config_path(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(p)
