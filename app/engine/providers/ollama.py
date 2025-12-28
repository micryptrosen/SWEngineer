# File: C:\Dev\CCP\SWEngineer\app\engine\providers\ollama.py
"""
Ollama provider (local LLM).

Requires:
- Ollama running locally (default: http://localhost:11434)
- A model pulled, e.g.:
    ollama pull llama3.1
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.types.messages import ChatMessage, Role


class OllamaError(RuntimeError):
    """Raised when Ollama cannot be reached or returns an error."""


@dataclass(frozen=True)
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "llama3.1"
    timeout_sec: float = 120.0


def _to_ollama_role(role: Role) -> str:
    if role in (Role.system, Role.user, Role.assistant):
        return role.value
    return "assistant"


def _to_ollama_messages(messages: List[ChatMessage]) -> List[Dict[str, str]]:
    return [{"role": _to_ollama_role(m.role), "content": m.content} for m in messages]


def _extract_text(resp_json: Dict[str, Any]) -> str:
    msg = resp_json.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(resp_json.get("response"), str):
        return str(resp_json["response"])
    return ""


class OllamaProvider:
    """
    Minimal Ollama chat provider.

    Uses:
      POST {host}/api/chat
    """

    def __init__(self, config: Optional[OllamaConfig] = None) -> None:
        self.config = config or OllamaConfig()

    def health(self) -> Tuple[bool, str]:
        url = f"{self.config.host.rstrip('/')}/api/tags"
        try:
            with httpx.Client(timeout=self.config.timeout_sec) as client:
                r = client.get(url)
                r.raise_for_status()
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def chat(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Returns: (assistant_text, meta)
        """
        url = f"{self.config.host.rstrip('/')}/api/chat"

        options: Dict[str, Any] = {
            "temperature": float(temperature),
            "top_p": float(top_p),
        }
        if max_tokens is not None:
            options["num_predict"] = int(max_tokens)
        if seed is not None:
            options["seed"] = int(seed)

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "stream": False,
            "messages": _to_ollama_messages(messages),
            "options": options,
        }

        try:
            with httpx.Client(timeout=self.config.timeout_sec) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
        except httpx.ConnectError as e:
            raise OllamaError(
                f"Ollama not reachable at {self.config.host}. Start Ollama and try again."
            ) from e
        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text
            except Exception:
                pass
            raise OllamaError(f"Ollama HTTP error: {e} {body}".strip()) from e
        except Exception as e:
            raise OllamaError(str(e)) from e

        text = _extract_text(data).strip()
        meta = {
            "model": self.config.model,
            "host": self.config.host,
            "raw": data,
        }
        return text, meta
