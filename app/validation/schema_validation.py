"""
Schema validation entrypoint (Phase 3 hardening).

LOCKED CONTRACTS:
- Vendor schema root is canonical: swe_schemas.resolve_schema_root() -> vendor/swe-schemas
- No silent fallback if vendor schemas are missing
- Public API (stable; used throughout app/tests):
    - SchemaValidationError
    - resolve_schema_root(schema_root: str | None) -> str
    - validate_payload(payload: dict, schema_root: str | None = None) -> None
"""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
from pathlib import Path
import json
from typing import Any, Optional

# Canonical plumbing bind (do not remove)
import swe_schemas as swe_schemas  # noqa: F401

import jsonschema


class SchemaValidationError(ValueError):
    pass


def resolve_schema_root(schema_root: Optional[str] = None) -> str:
    """
    Public API (stable):
    - If schema_root is provided, it is used (and must exist).
    - If schema_root is None, uses canonical swe_schemas.resolve_schema_root().
    - MUST raise SchemaValidationError if the resolved root does not exist.
    """
    root = Path(schema_root).resolve() if schema_root else Path(swe_schemas.resolve_schema_root()).resolve()
    if not root.exists():
        raise SchemaValidationError(f"vendor schema root missing (no fallback): {root}")
    if not root.is_dir():
        raise SchemaValidationError(f"schema root is not a directory: {root}")
    return str(root)


def _iter_candidate_schema_relpaths(contract: str) -> list[str]:
    """
    Generate likely schema filenames for a contract string.
    """
    c = (contract or "").strip()
    if not c:
        return []

    parts = c.split("/", 1)
    base = parts[0].strip()
    ver = parts[1].strip() if len(parts) == 2 else ""

    ver_norm = ver.replace(".", "_").replace("-", "_")
    base_norm = base.replace(".", "_").replace("-", "_")

    candidates: list[str] = []

    # Common patterns
    if base:
        candidates.append(f"schemas/{base}.schema.json")
        candidates.append(f"schemas/{base_norm}.schema.json")
        candidates.append(f"schemas/{base}.json")
        candidates.append(f"schemas/{base_norm}.json")

    if base and ver:
        candidates.append(f"schemas/{base}_{ver_norm}.schema.json")
        candidates.append(f"schemas/{base_norm}_{ver_norm}.schema.json")
        candidates.append(f"schemas/{base}_{ver_norm}.json")
        candidates.append(f"schemas/{base_norm}_{ver_norm}.json")

    # Slash-baked
    slash_norm = c.replace("/", "_").replace(".", "_").replace("-", "_")
    candidates.append(f"schemas/{slash_norm}.schema.json")
    candidates.append(f"schemas/{slash_norm}.json")

    # De-dupe keep order
    out: list[str] = []
    seen = set()
    for x in candidates:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _load_schema_obj(schema_path: Path) -> dict:
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SchemaValidationError(f"failed to load schema JSON: {schema_path}") from e


def _content_scan_find_schema(root: Path, contract: str) -> Optional[Path]:
    """
    Deterministic fallback:
    - scan vendor schemas under schemas/**/*.json in sorted path order
    - select the first file whose content includes the exact contract string
    """
    schemas_dir = (root / "schemas").resolve()
    if not schemas_dir.is_dir():
        return None

    # Deterministic order
    files = sorted([p for p in schemas_dir.rglob("*.json") if p.is_file()], key=lambda x: str(x).lower())
    needle = contract

    for fp in files:
        try:
            txt = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if needle in txt:
            return fp

    return None


def _resolve_schema_for_contract(root: Path, contract: str) -> Path:
    """
    Resolve the schema file path for a given contract.
    Hard-fails if not found. No non-vendor fallback.
    """
    # 1) Fast candidate filenames
    for rel in _iter_candidate_schema_relpaths(contract):
        p = (root / rel).resolve()
        if p.is_file():
            return p

    # 2) Deterministic content scan fallback (preferred to guessing names)
    found = _content_scan_find_schema(root, contract)
    if found is not None:
        return found.resolve()

    raise SchemaValidationError(f"no schema found for contract='{contract}' under {root}")


def validate_payload(payload: Any, schema_root: Optional[str] = None) -> None:
    """
    Public API (stable): validate a payload (dict or dataclass) against vendor schemas.

    - payload must include 'contract' field (string).
    - schema_root optional override; when None, uses canonical vendor/swe-schemas.
    """
    if is_dataclass(payload):
        payload = asdict(payload)

    if not isinstance(payload, dict):
        raise SchemaValidationError(f"payload must be dict-like; got {type(payload)}")

    contract = (payload.get("contract") or "").strip()
    if not contract:
        raise SchemaValidationError("payload missing required field: contract")

    root = Path(resolve_schema_root(schema_root)).resolve()
    schema_path = _resolve_schema_for_contract(root, contract)
    schema_obj = _load_schema_obj(schema_path)

    try:
        jsonschema.validate(instance=payload, schema=schema_obj)
    except jsonschema.ValidationError as e:
        raise SchemaValidationError(str(e)) from e
    except jsonschema.SchemaError as e:
        raise SchemaValidationError(str(e)) from e


__all__ = [
    "swe_schemas",
    "SchemaValidationError",
    "resolve_schema_root",
    "validate_payload",
]
