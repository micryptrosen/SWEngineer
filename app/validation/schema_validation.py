from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import swe_schemas


class SchemaValidationError(Exception):
    pass


def resolve_schema_root(schema_root: Optional[str] = None) -> str:
    """
    Phase3 invariant:
      - default resolves via swe_schemas.resolve_schema_root() (vendor-backed)
      - MUST NOT silently fall back if missing; must raise SchemaValidationError.
    """
    try:
        if schema_root is None:
            root = Path(swe_schemas.resolve_schema_root()).resolve()
        else:
            root = Path(str(schema_root)).resolve()
    except Exception as e:
        raise SchemaValidationError(f"failed to resolve schema root: {e}") from e

    if not root.exists():
        raise SchemaValidationError(f"vendor schema root missing: {root}")

    return str(root)


def _canonical_json_bytes(obj: Any, trailing_newline: bool = True) -> bytes:
    txt = json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    if trailing_newline:
        txt += "\n"
    return txt.encode("utf-8")


def _pretty_json_bytes(obj: Any, crlf: bool = False) -> bytes:
    txt = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if crlf:
        txt = txt.replace("\n", "\r\n")
    return txt.encode("utf-8")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _envelope_for_hash(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    SHA policy covers the entire top-level payload envelope, excluding the
    payload_sha256 field itself.
    """
    env = dict(payload)
    env.pop("payload_sha256", None)
    return env


def canonical_sha256_for_payload(payload: Dict[str, Any]) -> str:
    env = _envelope_for_hash(payload)
    return _sha256_hex(_canonical_json_bytes(env, trailing_newline=True))


def compute_payload_sha256(payload: Dict[str, Any]) -> str:
    """
    Public API (legacy name) used by tests/governance:
    returns canonical sha256 over the envelope (excluding payload_sha256).
    """
    return canonical_sha256_for_payload(payload)


def _legacy_sha_variants(payload: Dict[str, Any]) -> List[str]:
    env = _envelope_for_hash(payload)
    variants: List[str] = []

    # A: canonical (sorted keys, compact, with trailing newline)
    variants.append(_sha256_hex(_canonical_json_bytes(env, trailing_newline=True)))

    # B: canonical without trailing newline
    variants.append(_sha256_hex(_canonical_json_bytes(env, trailing_newline=False)))

    # C: pretty + LF
    variants.append(_sha256_hex(_pretty_json_bytes(env, crlf=False)))

    # D: pretty + CRLF
    variants.append(_sha256_hex(_pretty_json_bytes(env, crlf=True)))

    # de-dupe in order
    seen = set()
    out: List[str] = []
    for v in variants:
        if v not in seen:
            out.append(v)
            seen.add(v)
    return out


def payload_sha_is_accepted(payload: Dict[str, Any], declared_sha256: str) -> bool:
    d = (declared_sha256 or "").strip().lower()
    if not d:
        return False
    return d in _legacy_sha_variants(payload)


def validate_payload(payload: Dict[str, Any]) -> None:
    """
    Validate vendor schema payload and enforce (canonical + legacy-window) SHA policy.
    Raises SchemaValidationError on any validation failure.
    """
    if not isinstance(payload, dict):
        raise SchemaValidationError("payload must be an object")

    # Enforce resolver default (and existence) up-front.
    _ = resolve_schema_root(None)

    try:
        from app.validation.vendor_schema_loader import validate_against_vendor_schema
    except Exception as e:
        raise SchemaValidationError(f"validator wiring error: {e}") from e

    try:
        validate_against_vendor_schema(payload)
    except Exception as e:
        raise SchemaValidationError(str(e)) from e

    declared = payload.get("payload_sha256", "")
    if not isinstance(declared, str) or not declared.strip():
        raise SchemaValidationError("payload_sha256 missing")

    if not payload_sha_is_accepted(payload, declared):
        raise SchemaValidationError("payload_sha256 mismatch (not canonical and not within legacy window)")