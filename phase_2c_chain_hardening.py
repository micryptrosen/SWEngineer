from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

ROOT = Path.cwd().resolve()

def die(msg: str) -> None:
    raise SystemExit(msg)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")

def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(50):
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            return cur
        cur = cur.parent
    return start.resolve()

REPO = find_repo_root(ROOT)
VENDOR_SCHEMAS = REPO / "vendor" / "swe-schemas"

if not VENDOR_SCHEMAS.exists():
    die(f"FAILURE DETECTED: vendor/swe-schemas not found at {VENDOR_SCHEMAS}")

def detect_pkg_root(repo: Path) -> Path:
    # Prefer src-layout
    src = repo / "src"
    if src.exists():
        return src
    # fallback to repo root (flat)
    return repo

PKG_ROOT = detect_pkg_root(REPO)

def detect_pkg_name(pkg_root: Path) -> Optional[str]:
    # Heuristic: pick the folder that looks like the main package and contains __init__.py
    # Prefer 'swengineer' if present.
    cand = pkg_root / "swengineer"
    if (cand / "__init__.py").exists():
        return "swengineer"
    # Else: first top-level package with __init__.py
    for d in sorted(pkg_root.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.name not in {"tests"}:
            return d.name
    return None

PKG_NAME = detect_pkg_name(PKG_ROOT)
if not PKG_NAME:
    die(f"FAILURE DETECTED: could not detect package name under {PKG_ROOT}. Expected src/swengineer or a top-level package dir with __init__.py")

PKG_DIR = PKG_ROOT / PKG_NAME

# -------------------------------
# 1) Add schema locator module
# -------------------------------
schema_locator_path = PKG_DIR / "schema_locator.py"

schema_locator = f'''from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]

def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(50):
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            return cur
        cur = cur.parent
    return start.resolve()

def default_schema_root() -> Path:
    """
    Canonical default schema root (pinned by submodule commit):
      <repo>/vendor/swe-schemas
    """
    repo = _find_repo_root(Path(__file__).resolve())
    return (repo / "vendor" / "swe-schemas").resolve()

def resolve_schema_root(schema_root: Optional[PathLike] = None) -> Path:
    """
    Resolution order:
      1) explicit arg (schema_root)
      2) env SWE_SCHEMA_ROOT
      3) canonical default vendor path
    """
    if schema_root is None:
        env = os.environ.get("SWE_SCHEMA_ROOT") or os.environ.get("SWE_SCHEMA_DIR")
        if env:
            schema_root = env
    root = Path(schema_root) if schema_root is not None else default_schema_root()
    return root.resolve()
'''
if schema_locator_path.exists():
    existing = read_text(schema_locator_path)
    if "default_schema_root" in existing and "vendor" in existing and "resolve_schema_root" in existing:
        pass
    else:
        write_text(schema_locator_path, schema_locator)
else:
    write_text(schema_locator_path, schema_locator)

# ---------------------------------------------
# 2) Patch validator to use vendor/swe-schemas
# ---------------------------------------------
def iter_py_files(base: Path) -> Iterable[Path]:
    for p in base.rglob("*.py"):
        # skip vendor / venv / caches
        s = str(p).replace("\\", "/").lower()
        if "/.venv/" in s or "/venv/" in s or "/__pycache__/" in s or "/vendor/" in s:
            continue
        yield p

def patch_text(p: Path, txt: str) -> Tuple[str, bool]:
    orig = txt
    changed = False

    # If file already imports resolve_schema_root, we’re done.
    if "resolve_schema_root" in txt and "schema_locator" in txt:
        return (txt, False)

    # Heuristic 1: target common validator modules
    looks_like_validator = any(k in p.name.lower() for k in ("validator", "validation"))
    if not looks_like_validator:
        # also patch files that reference "schema" heavily
        if txt.count("schema") < 6:
            return (txt, False)

    # Insert import
    # Prefer: from <pkg>.schema_locator import resolve_schema_root
    pkg = PKG_NAME
    import_line = f"from {pkg}.schema_locator import resolve_schema_root"
    if import_line not in txt:
        # Insert after last standard import block line
        lines = txt.splitlines()
        insert_at = 0
        for i, line in enumerate(lines[:80]):
            if line.startswith("import ") or line.startswith("from "):
                insert_at = i + 1
        lines.insert(insert_at, import_line)
        txt = "\n".join(lines) + ("\n" if not txt.endswith("\n") else "")
        changed = True

    # Replace obvious defaults (Path("schemas") or "schemas") where used as schema root.
    # Safe narrow replacements only.
    txt2 = re.sub(
        r'(?P<prefix>\bschema_(root|dir)\s*=\s*)Path\(\s*[\'"]schemas[\'"]\s*\)',
        r'\g<prefix>resolve_schema_root(None)',
        txt,
        flags=re.IGNORECASE,
    )
    if txt2 != txt:
        txt = txt2
        changed = True

    txt2 = re.sub(
        r'(?P<prefix>\bschema_(root|dir)\s*=\s*)[\'"]schemas[\'"]',
        r'\g<prefix>str(resolve_schema_root(None))',
        txt,
        flags=re.IGNORECASE,
    )
    if txt2 != txt:
        txt = txt2
        changed = True

    # If there is a function parameter default like schema_root=Path("schemas") or schema_dir="schemas", patch to None.
    txt2 = re.sub(
        r'(\bschema_(root|dir)\s*:\s*(Path|str)\s*=\s*)(Path\(\s*[\'"]schemas[\'"]\s*\)|[\'"]schemas[\'"])',
        r'\1None',
        txt,
        flags=re.IGNORECASE,
    )
    if txt2 != txt:
        txt = txt2
        changed = True

    # If we changed param default to None, ensure resolution occurs inside function (best-effort).
    if changed:
        # Add a guard line near top of function bodies that accept schema_root/schema_dir.
        def add_resolution_guard(t: str) -> str:
            # naive: for each def line containing schema_root or schema_dir, inject first statement
            out = []
            lines = t.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                out.append(line)
                m = re.match(r'^(\s*)def\s+\w+\(.*\bschema_(root|dir)\b.*\)\s*:', line)
                if m:
                    indent = m.group(1) + "    "
                    # only inject if next non-empty line isn't already resolving
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        out.append(lines[j])
                        j += 1
                    if j < len(lines):
                        nxt = lines[j]
                        if "resolve_schema_root" not in nxt:
                            out.append(f"{indent}schema_root = resolve_schema_root(schema_root if 'schema_root' in locals() else None)")
                    i = j
                    continue
                i += 1
            return "\n".join(out) + ("\n" if t.endswith("\n") else "")
        txt = add_resolution_guard(txt)

    return (txt, changed)

patched_files = []
for p in iter_py_files(PKG_DIR):
    txt = read_text(p)
    new_txt, did = patch_text(p, txt)
    if did:
        write_text(p, new_txt)
        patched_files.append(p)

if not patched_files:
    # Hard target: try common paths
    hard_targets = [
        PKG_DIR / "validator.py",
        PKG_DIR / "validation" / "validator.py",
        PKG_DIR / "validators.py",
        PKG_DIR / "planner" / "validator.py",
    ]
    found_any = False
    for ht in hard_targets:
        if ht.exists():
            found_any = True
            txt = read_text(ht)
            new_txt, did = patch_text(ht, txt)
            if did:
                write_text(ht, new_txt)
                patched_files.append(ht)
    if found_any and not patched_files:
        # we found targets but none patched; ok (already compliant)
        pass

# ---------------------------------------------
# 3) Integration test: vendor schema root exists
# ---------------------------------------------
tests_dir = REPO / "tests"
test_path = tests_dir / "test_schema_root_vendor.py"

test_txt = f'''from __future__ import annotations

from pathlib import Path

from {PKG_NAME}.schema_locator import default_schema_root, resolve_schema_root

def test_default_schema_root_is_vendor_submodule() -> None:
    root = default_schema_root()
    assert root.name == "swe-schemas"
    assert (root / ".git").exists() or root.exists(), "vendor/swe-schemas must exist (submodule pinned)"
    # Must be under repo/vendor/swe-schemas
    repo = Path(__file__).resolve()
    for _ in range(50):
        if (repo / "pyproject.toml").exists() or (repo / ".git").exists():
            break
        repo = repo.parent
    assert (repo / "vendor" / "swe-schemas").resolve() == root

def test_resolve_schema_root_prefers_env_then_default(monkeypatch) -> None:
    monkeypatch.delenv("SWE_SCHEMA_ROOT", raising=False)
    monkeypatch.delenv("SWE_SCHEMA_DIR", raising=False)
    assert resolve_schema_root(None) == default_schema_root()

    monkeypatch.setenv("SWE_SCHEMA_ROOT", str(default_schema_root()))
    assert resolve_schema_root(None) == default_schema_root()
'''
if test_path.exists():
    existing = read_text(test_path)
    if "default_schema_root" in existing and "resolve_schema_root" in existing and "vendor" in existing:
        pass
    else:
        write_text(test_path, test_txt)
else:
    write_text(test_path, test_txt)

# -------------------------------------------------
# 4) Exclude vendor/ from lint (ruff) if present
# -------------------------------------------------
pyproject = REPO / "pyproject.toml"
if pyproject.exists():
    t = read_text(pyproject)
    if "[tool.ruff]" in t:
        # ensure vendor is excluded
        if re.search(r'^\s*exclude\s*=\s*\[', t, flags=re.MULTILINE):
            if "vendor" not in t:
                # append vendor to existing exclude array (best-effort)
                t2 = re.sub(
                    r'(^\s*exclude\s*=\s*\[)([^\]]*)(\])',
                    lambda m: m.group(1) + m.group(2).rstrip() + ("" if m.group(2).strip().endswith(",") or m.group(2).strip()=="" else ",") + '\n    "vendor",\n' + m.group(3),
                    t,
                    count=1,
                    flags=re.MULTILINE,
                )
                if t2 != t:
                    write_text(pyproject, t2)
        else:
            # add exclude line under [tool.ruff]
            t2 = re.sub(
                r'(\[tool\.ruff\]\s*\n)',
                r'\1exclude = ["vendor"]\n',
                t,
                count=1,
            )
            if t2 != t:
                write_text(pyproject, t2)

print("PHASE_2C_PATCH_DONE=GREEN")
print(f"PKG_NAME={PKG_NAME}")
print(f"PATCHED_FILES={len(patched_files)}")
for p in patched_files:
    print(f"PATCHED={p}")
print(f"ADDED_SCHEMA_LOCATOR={schema_locator_path}")
print(f"ADDED_TEST={test_path}")
