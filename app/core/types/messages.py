# File: C:\Dev\CCP\SWEngineer\app\core\types\messages.py
"""
Core message + event models for the Engineer runtime.

These are generic and will be used by:
- GUI chat panel
- Local engine provider (Ollama / LM Studio / etc.)
- Tooling (file write, command run, verification)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class EventType(str, Enum):
    chat = "chat"
    plan = "plan"
    file_write = "file_write"
    command = "command"
    verify = "verify"
    status = "status"
    error = "error"


class ChatMessage(BaseModel):
    id: str = Field(..., description="Client-generated id (uuid recommended).")
    role: Role
    content: str
    created_at: datetime = Field(default_factory=utc_now)


class FileWrite(BaseModel):
    path: str = Field(..., description="Project-relative or absolute path.")
    content: str = Field(..., description="Full file content to write (whole-file replacement).")
    encoding: str = "utf-8"


class CommandRun(BaseModel):
    cwd: Optional[str] = Field(default=None, description="Working directory (project root if omitted).")
    command: List[str] = Field(..., description="Process argv, e.g. ['powershell','-NoProfile',...].")
    timeout_sec: int = 120


class VerifyRequest(BaseModel):
    path: str
    kind: Literal["py_compile", "json"] = "py_compile"


class VerifyResult(BaseModel):
    path: str
    ok: bool
    stdout: str = ""
    stderr: str = ""


class EngineerEvent(BaseModel):
    type: EventType
    created_at: datetime = Field(default_factory=utc_now)
    message: Optional[ChatMessage] = None
    plan: Optional[str] = None
    file_write: Optional[FileWrite] = None
    command: Optional[CommandRun] = None
    verify: Optional[VerifyResult] = None
    status: Optional[str] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
