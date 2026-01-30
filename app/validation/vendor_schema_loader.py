from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json

import jsonschema
from referencing import Registry, Resource

# -------------------------------------------------------------------
# Phase5 / Step5IM:
# Replace deprecated jsonschema.RefResolver usage with referencing.Registry.
# Goal: preserve existing behavior while removing DeprecationWarning source.
# -------------------------------------------------------------------

def _repo_root() -> Path:
    # vendor_schema_loader.py lives at: app/validation/vendor_schema_loader.py
    # repo root is 3 parents up (vendor_schema_loader.py -> validation -> app -> repo)
    return Path(__file__).resolve().parents[2]

def _safe_read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def _as_file_uri(p: Path) -> str:
    # Path.as_uri() requires absolute path
    return p.resolve().as_uri()

def _build_registry(schema_root: Path) -> Registry:
    """
    Build a referencing.Registry containing *all* JSON resources under schema_root.
    Preference order for resource URI:
      1) $id if present
      2) file:// URI of the json file path
    """
    schema_root = Path(schema_root).resolve()
    reg = Registry()
    for fp in sorted(schema_root.rglob("*.json")):
        try:
            doc = _safe_read_json(fp)
        except Exception:
            # Skip non-JSON or unreadable files quietly; schemas should be valid JSON.
            continue

        uri = None
        if isinstance(doc, dict):
            _id = doc.get("$id")
            if isinstance(_id, str) and _id.strip():
                uri = _id.strip()

        if not uri:
            uri = _as_file_uri(fp)

        # Resource.from_contents lets referencing infer the spec as needed.
        res = Resource.from_contents(doc)
        reg = reg.with_resource(uri, res)

    return reg

def _resolve_schema_root(schema_root: Optional[Path]) -> Path:
    """
    Default: vendor/swe-schemas (via swe_schemas.resolve_schema_root()).
    No fallback allowed: if missing, raise immediately.
    """
    if schema_root is None:
        import swe_schemas  # vendor-pinned package
        schema_root = Path(swe_schemas.resolve_schema_root())
    schema_root = Path(schema_root).resolve()
    if not schema_root.exists():
        raise FileNotFoundError(f"schema_root does not exist: {schema_root}")
    return schema_root

def _resolve_schema_path(contract: str, schema_root: Path) -> Path:
    """
    Resolve schema file path for a contract id like 'run_handoff/1.0'.

    Preferred: ask swe_schemas for a contract->path resolver if present.
    Fallback: search for a JSON file whose contents declare the same title/id.
    """
    # 1) Prefer explicit resolver if present (keeps behavior aligned with vendor package)
    import swe_schemas
    if hasattr(swe_schemas, "resolve_schema_path"):
        p = Path(swe_schemas.resolve_schema_path(contract)).resolve()
        return p
    if hasattr(swe_schemas, "resolve_contract_schema_path"):
        p = Path(swe_schemas.resolve_contract_schema_path(contract)).resolve()
        return p

    # 2) Fallback: scan for a schema with title == contract OR $id ending with contract
    contract_norm = str(contract).strip()
    for fp in sorted(schema_root.rglob("*.json")):
        try:
            doc = _safe_read_json(fp)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue

        title = doc.get("title")
        _id = doc.get("$id")

        if title == contract_norm:
            return fp.resolve()

        if isinstance(_id, str) and _id.strip().endswith(contract_norm):
            return fp.resolve()

        # Some schemas may use "type"/const patterns; keep conservative.

    raise FileNotFoundError(f"could not resolve schema for contract '{contract_norm}' under {schema_root}")

def validate_against_vendor_schema(payload: Dict[str, Any], schema_root: Optional[Path] = None) -> None:
    """
    Validate payload against vendor schema corresponding to payload['contract'].

    NOTE:
    - Uses referencing.Registry (no jsonschema.RefResolver).
    - Ensures all refs resolve from vendor schema tree.
    """
    schema_root_p = _resolve_schema_root(schema_root)
    contract = payload.get("contract")
    if not isinstance(contract, str) or not contract.strip():
        raise ValueError("payload.contract must be a non-empty string")

    schema_path = _resolve_schema_path(contract.strip(), schema_root_p)
    schema = _safe_read_json(schema_path)

    # Build registry rooted in vendor schema tree.
    # This is stricter and future-proof vs RefResolver.
    registry = _build_registry(schema_root_p)

    # Ensure the "entry" schema is registered by a stable URI too (file URI at minimum).
    # This helps if the entry has relative refs without $id.
    entry_uri = None
    if isinstance(schema, dict):
        _id = schema.get("$id")
        if isinstance(_id, str) and _id.strip():
            entry_uri = _id.strip()
    if not entry_uri:
        entry_uri = _as_file_uri(schema_path)

    registry = registry.with_resource(entry_uri, Resource.from_contents(schema))

    v_cls = jsonschema.validators.validator_for(schema)
    v_cls.check_schema(schema)

    # IMPORTANT: pass registry=... (no resolver kwarg)
    v = v_cls(schema, registry=registry)

    # Validate payload (raises jsonschema.ValidationError on failure)
    v.validate(payload)
