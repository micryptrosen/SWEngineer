from __future__ import annotations
from pathlib import Path
import sys

p = Path(r"C:\Dev\CCP\SWEngineer\.github\workflows\ci.yml")
raw = p.read_text(encoding="utf-8", errors="strict")
if not raw.strip():
    raise SystemExit("CI_YML_EMPTY")
if "jobs:" not in raw or "on:" not in raw:
    raise SystemExit("CI_YML_MISSING_KEYS")

try:
    import yaml  # type: ignore
except Exception:
    print("CI_YML_BASIC_OK (PyYAML not installed)")
    raise SystemExit(0)

obj = yaml.safe_load(raw)
if not isinstance(obj, dict):
    raise SystemExit("CI_YML_NOT_MAP")
print("CI_YML_PARSE_OK")
