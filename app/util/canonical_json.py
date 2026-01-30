from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_dumps(obj: Any) -> str:
    """
    Deterministic JSON text:
      - sort_keys=True
      - indent=2
      - UTF-8 safe (ensure_ascii=False)
      - trailing newline
    """
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def canonical_sha256_for_payload(payload: Dict[str, Any]) -> str:
    """
    Canonical SHA256 over payload-without-sha.
    """
    p = dict(payload)
    p.pop("payload_sha256", None)
    b = canonical_dumps(p).encode("utf-8")
    return hashlib.sha256(b).hexdigest()
