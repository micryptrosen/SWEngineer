from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


class SchemaValidationError(Exception):
    pass


def _canonical_json_bytes(obj: Any) -> bytes:
    """
    Canonical JSON bytes: stable key ordering, no trailing spaces, LF newline.
    """
    txt = json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return (txt + "\n").encode("utf-8")


def compute_payload_sha256(payload: Dict[str, Any]) -> str:
    """
    Canonical payload SHA256 (hex) for run_handoff payload bodies.
    """
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _legacy_sha_variants(payload: Dict[str, Any]) -> List[str]:
    """
    Legacy compatibility window:
    Return a list of allowed sha256 hex digests that historically appeared in producers
    before canonicalization was unified.

    Governance rule: all accepted legacy variants MUST be generated here and locked by tests.
    """
    variants: List[str] = []

    # Variant A: canonical bytes (current)
    variants.append(hashlib.sha256(_canonical_json_bytes(payload)).hexdigest())

    # Variant B: canonical JSON without trailing newline
    txt = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    variants.append(hashlib.sha256(txt.encode("utf-8")).hexdigest())

    # Variant C: pretty JSON (indent=2, sort_keys) + LF
    txt_pretty_lf = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    variants.append(hashlib.sha256(txt_pretty_lf.encode("utf-8")).hexdigest())

    # Variant D: pretty JSON (indent=2, sort_keys) + CRLF
    txt_pretty_crlf = txt_pretty_lf.replace("\n", "\r\n")
    variants.append(hashlib.sha256(txt_pretty_crlf.encode("utf-8")).hexdigest())

    # De-dup while preserving order
    seen = set()
    out: List[str] = []
    for v in variants:
        if v not in seen:
            out.append(v)
            seen.add(v)
    return out


def payload_sha_is_accepted(payload_body: Dict[str, Any], declared_sha256: str) -> bool:
    """
    Returns True if declared_sha256 matches canonical or allowed legacy variants.
    """
    d = (declared_sha256 or "").strip().lower()
    if not d:
        return False
    return d in _legacy_sha_variants(payload_body)


def validate_payload(payload: Dict[str, Any]) -> None:
    """
    Validate vendor schema payload and enforce (canonical + legacy-window) SHA policy.
    Raises SchemaValidationError on any validation failure.
    """
    # Import here to avoid import cycles in app boot.
    from app.validation.vendor_schema_loader import validate_against_vendor_schema

    validate_against_vendor_schema(payload)

    # SHA enforcement: for run_handoff payloads, confirm payload_sha256 aligns with allowed window
    try:
        body = payload.get("payload", {})
        declared = payload.get("payload_sha256", "")
    except Exception as e:
        raise SchemaValidationError(f"Invalid payload structure: {e}") from e

    if not isinstance(body, dict):
        raise SchemaValidationError("payload.payload must be an object")

    if not payload_sha_is_accepted(body, str(declared)):
        raise SchemaValidationError("payload_sha256 mismatch (not canonical and not within legacy window)")