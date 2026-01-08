# File: C:\Dev\CCP\SWEngineer\app\engine\actions.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# JSON actions schema (reference):
# {
#   "final_message": "string (optional)",
#   "actions": [
#     {"type": "file_write", "path": "relative/or/absolute", "content": "FULL FILE CONTENT"},
#     {"type": "verify", "path": "relative/or/absolute"},
#     {"type": "open", "path": "relative/or/absolute"},
#     {"type": "message", "text": "string"}
#   ]
# }


@dataclass(frozen=True)
class FileBlock:
    path: str
    content: str


@dataclass(frozen=True)
class EngineerAction:
    type: str
    data: Dict[str, Any]


@dataclass(frozen=True)
class EngineerPayload:
    final_message: str
    actions: List[EngineerAction]


_JSON_FENCE_RE = re.compile(r"```json\s*\n(.*?)```", flags=re.DOTALL | re.IGNORECASE)
_ANY_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_+\-]+)?\n(.*?)```", flags=re.DOTALL)


def _try_parse_json(s: str) -> Optional[Dict[str, Any]]:
    s = s.strip()
    if not s:
        return None
    try:
        obj = json.loads(s)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = text or ""

    for m in _JSON_FENCE_RE.finditer(text):
        obj = _try_parse_json(m.group(1))
        if obj is not None:
            return obj

    stripped = text.lstrip()
    if stripped.startswith("{"):
        obj = _try_parse_json(stripped)
        if obj is not None:
            return obj

    return None


def parse_engineer_payload(text: str) -> Optional[EngineerPayload]:
    obj = extract_json_object(text)
    if obj is None:
        return None

    final_message = obj.get("final_message")
    if not isinstance(final_message, str):
        final_message = ""

    raw_actions = obj.get("actions")
    if not isinstance(raw_actions, list):
        raw_actions = []

    actions: List[EngineerAction] = []
    for item in raw_actions:
        if not isinstance(item, dict):
            continue
        t = item.get("type")
        if not isinstance(t, str) or not t.strip():
            continue
        data: Dict[str, Any] = {k: v for k, v in item.items() if k != "type"}
        actions.append(EngineerAction(type=t.strip(), data=data))

    return EngineerPayload(final_message=final_message, actions=actions)


def extract_file_blocks_from_markdown(text: str) -> List[FileBlock]:
    blocks: List[FileBlock] = []
    text = text or ""

    for m in _ANY_FENCE_RE.finditer(text):
        body = m.group(1)
        lines = body.splitlines()
        if not lines:
            continue
        first = lines[0].strip()
        if not first.lower().startswith("# file:"):
            continue
        file_path = first.split(":", 1)[1].strip()
        content = "\n".join(lines[1:]).lstrip("\n")
        if file_path:
            blocks.append(FileBlock(path=file_path, content=content))

    return blocks


def payload_to_file_blocks(payload: EngineerPayload) -> List[FileBlock]:
    blocks: List[FileBlock] = []
    for a in payload.actions:
        if a.type != "file_write":
            continue
        p = a.data.get("path")
        c = a.data.get("content")
        if isinstance(p, str) and p.strip() and isinstance(c, str):
            blocks.append(FileBlock(path=p.strip(), content=c))
    return blocks
