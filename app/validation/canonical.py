from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization used for hashing/signing.

    Rules:
      - sort_keys=True
      - compact separators
      - ensure_ascii=False
      - stable across dict insertion order
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), indent=None)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_payload_sha256(payload_no_sha: Dict[str, Any]) -> str:
    """Compute payload_sha256 over the payload WITHOUT payload_sha256 field."""
    if "payload_sha256" in payload_no_sha:
        raise ValueError("compute_payload_sha256 expects payload without 'payload_sha256'")
    return sha256_hex(canonical_json(payload_no_sha))


def verify_payload_sha256(payload_with_sha: Dict[str, Any]) -> bool:
    """Verify payload_sha256 matches canonical hash of payload minus payload_sha256."""
    if "payload_sha256" not in payload_with_sha:
        return False
    got = payload_with_sha.get("payload_sha256")
    if not isinstance(got, str) or len(got) != 64:
        return False
    p = dict(payload_with_sha)
    p.pop("payload_sha256", None)
    want = compute_payload_sha256(p)
    return got == want
