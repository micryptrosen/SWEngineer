# File: C:\Dev\CCP\SWEngineer\app\engine\engine.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

_JSON_ONLY_SYSTEM_PROMPT = (
    "You are a local AI software engineer.\n"
    "You MUST respond with ONLY a single JSON object (no markdown, no code fences, no extra text).\n"
    "Schema:\n"
    "{\n"
    '  "final_message": "string (optional)",\n'
    '  "actions": [\n'
    '    {"type":"file_write","path":"relative/or/absolute","content":"FULL FILE CONTENT"},\n'
    '    {"type":"verify","path":"relative/or/absolute"},\n'
    '    {"type":"open","path":"relative/or/absolute"},\n'
    '    {"type":"message","text":"string"}\n'
    "  ]\n"
    "}\n"
    "If you are not writing files, return an empty actions array.\n"
    "Never include backticks. Never include non-JSON text.\n"
)


@dataclass(frozen=True)
class EngineConfig:
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    system_prompt: str = _JSON_ONLY_SYSTEM_PROMPT
    timeout_seconds: float = 120.0


class Engine:
    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        base = config or EngineConfig()
        self.config = EngineConfig(
            ollama_host=os.getenv("OLLAMA_HOST", base.ollama_host),
            ollama_model=os.getenv("OLLAMA_MODEL", base.ollama_model),
            system_prompt=os.getenv("ENGINEER_SYSTEM_PROMPT", base.system_prompt),
            timeout_seconds=base.timeout_seconds,
        )
        self._messages: List[Dict[str, str]] = []
        self.reset()

    def reset(self) -> None:
        self._messages = [{"role": "system", "content": self.config.system_prompt}]

    def health(self) -> Tuple[bool, str]:
        url = self._join("/api/tags")
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                r = client.get(url)
                if r.status_code >= 400:
                    return False, f"{r.status_code} {r.text}"
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def send_user(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        self._messages.append({"role": "user", "content": text})

        payload: Dict[str, Any] = {
            "model": self.config.ollama_model,
            "messages": self._messages,
            "stream": False,
        }

        url = self._join("/api/chat")
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e

        msg = data.get("message") or {}
        content = (msg.get("content") or "").strip()
        if content:
            self._messages.append({"role": "assistant", "content": content})
        return content

    def _join(self, path: str) -> str:
        host = (self.config.ollama_host or "").rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return host + path
