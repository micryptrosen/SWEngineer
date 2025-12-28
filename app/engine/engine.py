# File: C:\Dev\CCP\SWEngineer\app\engine\engine.py
"""
Engineer runtime (in-process).

Responsibilities:
- Maintain chat history
- Call a provider (Ollama first)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Tuple
from uuid import uuid4

from app.core.types.messages import ChatMessage, Role
from app.engine.providers.ollama import OllamaConfig, OllamaError, OllamaProvider


@dataclass(frozen=True)
class EngineConfig:
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    system_prompt: str = (
        "You are a local AI software engineer. "
        "Respond with whole-file replacements when asked to modify files. "
        "Keep responses short and operational."
    )


class Engine:
    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        base = config or EngineConfig()
        self.config = EngineConfig(
            ollama_host=os.getenv("OLLAMA_HOST", base.ollama_host),
            ollama_model=os.getenv("OLLAMA_MODEL", base.ollama_model),
            system_prompt=os.getenv("ENGINEER_SYSTEM_PROMPT", base.system_prompt),
        )
        self.provider = OllamaProvider(
            OllamaConfig(host=self.config.ollama_host, model=self.config.ollama_model)
        )
        self._messages: List[ChatMessage] = []
        self.reset()

    @property
    def messages(self) -> List[ChatMessage]:
        return list(self._messages)

    def reset(self) -> None:
        self._messages = [
            ChatMessage(id=self._new_id(), role=Role.system, content=self.config.system_prompt)
        ]

    def health(self) -> Tuple[bool, str]:
        return self.provider.health()

    def send_user(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""

        self._messages.append(ChatMessage(id=self._new_id(), role=Role.user, content=text))

        try:
            reply, _meta = self.provider.chat(self._messages)
        except OllamaError as e:
            raise RuntimeError(str(e)) from e

        reply = (reply or "").strip()
        if reply:
            self._messages.append(
                ChatMessage(id=self._new_id(), role=Role.assistant, content=reply)
            )
        return reply

    @staticmethod
    def _new_id() -> str:
        return str(uuid4())
