# File: C:\Dev\CCP\SWEngineer\app\validation\schema_validation.py
from __future__ import annotations

import importlib.util as _importlib_util
import json
import re
import sys as _sys
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema
from app.util.canonical_json import canonical_sha256_for_payload

def _legacy_sha256_for_payload(payload: Dict[str, Any]) -> str:
    """
    Compatibility digests for pre-Step5IE producers and vendor fixtures.

    We accept a small, explicit set of legacy canonicalization styles:
      A) compact JSON: separators=(',', ':'), ensure_ascii=True
      B) pretty JSON: indent=2, sort_keys=True, ensure_ascii=False, with trailing '\\n'
      C) pretty JSON: indent=2, sort_keys=True, ensure_ascii=False, no trailing newline

    We return the FIRST variant's digest (A) for callers that want "a legacy digest",
    but _enforce_payload_sha256() may compare against multiple variants by calling
    _legacy_sha256_variants_for_payload().
    """
    return _legacy_sha256_variants_for_payload(payload)[0]

def _legacy_sha256_variants_for_payload(payload: Dict[str, Any]) -> List[str]:
    p = dict(payload)
    p.pop("payload_sha256", None)

    variants: List[bytes] = []

    # A) compact
    txt_a = json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    variants.append(txt_a.encode("utf-8"))

    # B) pretty + newline (most common fixture style)
    txt_b = json.dumps(p, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    variants.append(txt_b.encode("utf-8"))

    # C) pretty (no newline)
    txt_c = json.dumps(p, sort_keys=True, indent=2, ensure_ascii=False)
    variants.append(txt_c.encode("utf-8"))

    out: List[str] = []
    for b in variants:
        out.append(hashlib.sha256(b).hexdigest())
    return out


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




def _registry_from_store(store: Dict[str, Any]) -> "Registry":
    """
    Build a referencing.Registry from our explicit store mapping.

    Determinism + vendor-root-only:
      - ONLY URIs present in `store` are resolvable
      - no filesystem/network fetch is allowed or used
    """
    reg = Registry()
    for uri, schema in (store or {}).items():
        reg = reg.with_resource(uri, to_cached_resource(schema))
    return reg

def _validate_with_refs(payload: Dict[str, Any], schema: Dict[str, Any], schema_path: Path, store: Dict[str, Any]) -> None:
    """
    Validate payload against schema, resolving $refs ONLY from the explicit in-memory store.

    This removes referencing.Registry (deprecated) and uses the referencing.Registry path
    while preserving:
      - vendor-root-only resolution (no ambient discovery)
      - deterministic behavior under python -I
      - local $ref behavior (relative refs resolve against schema $id / file URI)
    """
    if "$id" not in schema:
        schema["$id"] = schema_path.resolve().as_uri()

    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)

        registry = _registry_from_store(store)
        v = validator_cls(schema, registry=registry)

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

def _enforce_payload_sha256(payload: Dict[str, Any], *, strict: bool = True) -> None:
    """
    Phase 2E invariant + compatibility window:
      - payload_sha256 must exist
      - must be 64 lowercase hex
      - when strict=True: must verify against either:
          (a) Step5IE canonical digest (preferred)
          (b) legacy digest used by pre-Step5IE producers + vendor fixtures
    """
    got = payload.get("payload_sha256")
    if not isinstance(got, str):
        raise SchemaValidationError("payload_sha256 is required")
    if not _SHA256_RE.match(got):
        raise SchemaValidationError("payload_sha256 must be 64 lowercase hex")

    if strict:
        want_new = canonical_sha256_for_payload(payload)
        if got == want_new:
            return
        for want_legacy in _legacy_sha256_variants_for_payload(payload):
            if got == want_legacy:
                return
        raise SchemaValidationError("payload_sha256 does not match canonical or any known legacy payload digest")


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
    _enforce_payload_sha256(payload, strict=strict)

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
