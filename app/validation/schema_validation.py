from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.schema_locator import resolve_schema_root

class SchemaValidationError(RuntimeError):
    pass

def _iter_json_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*.json"):
        # ignore tooling / hidden dirs
        s = str(p).replace("\\", "/")
        if "/.git/" in s or "/__pycache__/" in s:
            continue
        out.append(p)
    return out

def _normalize_contract(contract: str) -> str:
    return contract.strip().lower()

def find_schema_for_contract(contract: str, schema_root: Optional[Path] = None) -> Path:
    """
    Best-effort resolver.
    Primary: schema_root/<contract>.json (supports subfolders if contract contains '/')
    Fallback: recursive search for JSON file whose path contains the normalized contract tokens.
    """
    root = resolve_schema_root(schema_root)
    if not root.exists():
        raise SchemaValidationError(f"schema_root does not exist: {root}")

    c = _normalize_contract(contract)

    # 1) direct: <root>/<contract>.json
    direct = (root / (c + ".json"))
    if direct.exists():
        return direct

    # 2) direct with path segments: <root>/<contract>.json (contract may include '/')
    direct2 = (root / Path(c + ".json"))
    if direct2.exists():
        return direct2

    # 3) common pattern: <root>/<contract>/schema.json
    direct3 = (root / Path(c) / "schema.json")
    if direct3.exists():
        return direct3

    # 4) recursive token match
    tokens = [t for t in re.split(r"[^a-z0-9]+", c) if t]
    candidates: list[Path] = []
    for p in _iter_json_files(root):
        s = str(p).replace("\\", "/").lower()
        if all(t in s for t in tokens):
            candidates.append(p)

    if not candidates:
        raise SchemaValidationError(f"no schema found for contract='{contract}' under {root}")

    # Prefer shortest path (most specific)
    candidates.sort(key=lambda p: (len(str(p)), str(p)))
    return candidates[0]

def validate_payload(payload: Dict[str, Any], schema_root: Optional[Path] = None) -> None:
    """
    Validates payload against the schema resolved by payload['contract'].
    Requires jsonschema to be installed; errors raise SchemaValidationError.
    """
    if "contract" not in payload or not isinstance(payload["contract"], str) or not payload["contract"].strip():
        raise SchemaValidationError("payload missing required string field: contract")

    contract = payload["contract"]
    schema_path = find_schema_for_contract(contract, schema_root=schema_root)

    try:
        import jsonschema  # type: ignore
    except Exception as e:
        raise SchemaValidationError("jsonschema is required for validation but is not available") from e

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except Exception as e:
        raise SchemaValidationError(f"schema validation failed for contract='{contract}' schema='{schema_path}'") from e
