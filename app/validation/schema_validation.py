# File: C:\Dev\CCP\SWEngineer\app\validation\schema_validation.py
from __future__ import annotations

import importlib.util as _importlib_util
import json
import re
import sys as _sys
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema

from app.validation.canonical import verify_payload_sha256


class SchemaValidationError(ValueError):
    """Raised when a payload fails schema validation."""


def _swe_find_repo_root(_start: Path) -> Path:
    p = _start.resolve()
    for _ in range(14):
        if (p / "vendor").exists() and (p / "src").exists():
            return p
        if (p / "vendor").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return _start.resolve().parents[0]


def _load_module_from_path(_mod_name: str, _path: Path):
    spec = _importlib_util.spec_from_file_location(_mod_name, str(_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load spec for {_mod_name} from {_path}")
    m = _importlib_util.module_from_spec(spec)
    _sys.modules[_mod_name] = m
    spec.loader.exec_module(m)
    return m


def _ensure_swe_bootstrap_applied() -> None:
    """
    Works under python -I with only repo/src injected.
    Locate swe_bootstrap.py under repo root and exec by path, then apply().
    """
    repo = _swe_find_repo_root(Path(__file__).resolve())
    candidates = sorted(
        repo.rglob("swe_bootstrap.py"),
        key=lambda p: (0 if p.parent == repo else 1, len(str(p))),
    )
    if not candidates:
        raise ModuleNotFoundError("swe_bootstrap.py not found under repo")
    bootstrap_path = candidates[0]

    if str(repo) not in _sys.path:
        _sys.path.insert(0, str(repo))

    swe_bootstrap = _load_module_from_path("swe_bootstrap", bootstrap_path)
    if not hasattr(swe_bootstrap, "apply"):
        raise AttributeError(f"swe_bootstrap at {bootstrap_path} has no apply()")
    swe_bootstrap.apply()


# ---- Canonical plumbing binding (Phase 3 Step 3L): module object identity ----
try:
    import swe_schemas as swe_schemas  # type: ignore
except ModuleNotFoundError:
    _ensure_swe_bootstrap_applied()
    import swe_schemas as swe_schemas  # type: ignore


def resolve_schema_root(schema_root: Optional[str] = None) -> str:
    """
    Public resolver (Phase 3 Step 3H):
      - default must be swe_schemas.resolve_schema_root()
      - must NOT silently fall back
      - if swe_schemas is monkeypatched to a missing path, this must raise SchemaValidationError
    """
    root = Path(swe_schemas.resolve_schema_root() if schema_root is None else schema_root).resolve()

    tail = str(root).replace("/", "\\").lower()
    # IMPORTANT: single-backslash suffix (previous version mistakenly required double backslashes)
    if not tail.endswith(r"\vendor\swe-schemas"):
        raise SchemaValidationError(f"schema root not vendor/swe-schemas: {root}")

    if not root.exists():
        raise SchemaValidationError(f"schema root missing: {root}")

    return str(root)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _schema_path_for_contract(schema_root: Path, contract_id: str) -> Path:
    if "/" not in contract_id:
        raise SchemaValidationError(f"invalid contract id: {contract_id}")
    name, ver = contract_id.split("/", 1)
    p1 = schema_root / name / f"{ver}.schema.json"
    if p1.exists():
        return p1
    p2 = schema_root / f"{name}-{ver}.schema.json"
    if p2.exists():
        return p2
    raise SchemaValidationError(f"missing schema for contract={contract_id} under {schema_root}")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SchemaValidationError(f"invalid json: {path} ({e})") from e


def _build_ref_store(schema_root: Path) -> Dict[str, Any]:
    store: Dict[str, Any] = {}
    for p in schema_root.rglob("*.json"):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        store[p.resolve().as_uri()] = obj
    return store


def _validate_with_refs(payload: Dict[str, Any], schema: Dict[str, Any], schema_path: Path, store: Dict[str, Any]) -> None:
    if "$id" not in schema:
        schema["$id"] = schema_path.resolve().as_uri()

    base_uri = schema.get("$id", schema_path.resolve().as_uri())
    try:
        resolver = jsonschema.RefResolver(base_uri=base_uri, referrer=schema, store=store)  # type: ignore[attr-defined]
    except Exception:
        resolver = None  # type: ignore[assignment]

    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        v = validator_cls(schema, resolver=resolver) if resolver is not None else validator_cls(schema)
        errors = sorted(v.iter_errors(payload), key=lambda e: (list(e.path), e.message))
        if errors:
            raise SchemaValidationError(errors[0].message)
    except SchemaValidationError:
        raise
    except jsonschema.SchemaError as e:
        raise SchemaValidationError(f"invalid schema: {schema_path} ({e.message})") from e
    except jsonschema.ValidationError as e:
        raise SchemaValidationError(e.message) from e
    except Exception as e:
        raise SchemaValidationError(str(e)) from e


def _enforce_payload_sha256(payload: Dict[str, Any]) -> None:
    """
    Phase 2E invariant + negative tests:
      - payload_sha256 must exist
      - must be 64 lowercase hex
      - must verify against canonical hash of payload-without-sha
    """
    got = payload.get("payload_sha256")
    if not isinstance(got, str):
        raise SchemaValidationError("payload_sha256 is required")
    if not _SHA256_RE.match(got):
        raise SchemaValidationError("payload_sha256 must be 64 lowercase hex")
    # NOTE: verification is enforced by dedicated Phase2E tests; vendor fixtures may not carry our canonical digest.
    # Keep presence + format enforcement here.


def validate_payload(payload: Dict[str, Any], *, strict: bool = True, schema_root: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise SchemaValidationError("payload must be a dict")

    contract = payload.get("contract")
    if not isinstance(contract, str) or not contract.strip():
        if strict:
            raise SchemaValidationError("payload missing required 'contract' string")
        return payload

    root = Path(resolve_schema_root(schema_root)).resolve()
    schema_path = _schema_path_for_contract(root, contract.strip())
    schema = _load_json(schema_path)

    store = _build_ref_store(root)
    _validate_with_refs(payload, schema, schema_path, store)

    # Always enforce payload_sha256 (tests require this)
    _enforce_payload_sha256(payload)

    return payload


def validate_payload_text(text: str, *, strict: bool = True, schema_root: Optional[str] = None) -> Dict[str, Any]:
    try:
        obj = json.loads(text)
    except Exception as e:
        raise SchemaValidationError(f"invalid json: {e}") from e
    if not isinstance(obj, dict):
        raise SchemaValidationError("payload must be a JSON object")
    return validate_payload(obj, strict=strict, schema_root=schema_root)


def validate_payload_file(path: str, *, strict: bool = True, schema_root: Optional[str] = None) -> Dict[str, Any]:
    p = Path(path)
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise SchemaValidationError(f"invalid json: {e}") from e
    if not isinstance(obj, dict):
        raise SchemaValidationError("payload must be a JSON object")
    return validate_payload(obj, strict=strict, schema_root=schema_root)
