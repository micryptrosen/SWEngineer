from __future__ import annotations
import swe_bootstrap as _swe_bootstrap
_swe_bootstrap.apply()


from pathlib import Path
import re

ROOT = Path.cwd().resolve()
APP = ROOT / "app"
TESTS = ROOT / "tests"

def die(msg: str) -> None:
    raise SystemExit(msg)

def write(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s.replace("\r\n", "\n").replace("\r", "\n") + "\n", encoding="utf-8", newline="\n")

def patch_pyproject_exclude_vendor(pyproject: Path) -> bool:
    if not pyproject.exists():
        die("pyproject.toml not found")

    txt = pyproject.read_text(encoding="utf-8")

    # We exclude vendor/ from lint in SWEngineer (submodules validated in their repos).
    # Targets common configs (ruff, black, isort); patch idempotently.
    changed = False

    def ensure_ruff(t: str) -> str:
        nonlocal changed
        if "[tool.ruff]" not in t:
            return t
        # Ensure exclude includes "vendor"
        # Prefer TOML array form: exclude = ["vendor", ...]
        # If exclude already mentions vendor, do nothing.
        if re.search(r"^\s*exclude\s*=\s*\[[^\]]*(\"vendor\"|'vendor')[^\]]*\]\s*$", t, flags=re.M):
            return t
        # If exclude exists, append vendor; otherwise insert exclude.
        m = re.search(r'^\s*exclude\s*=\s*\[(.*?)\]\s*$', t, flags=re.M)
        if m:
            inner = m.group(1).strip()
            inner2 = (inner + ", " if inner else "") + '"vendor"'
            t2 = t[:m.start()] + re.sub(r'^\s*exclude\s*=\s*\[(.*?)\]\s*$',
                                        f'exclude = [{inner2}]',
                                        t[m.start():t[m.end():].start() if False else m.end()],
                                        flags=re.M)
            # Above is too fancy; do simpler slice replacement:
            t2 = t[:m.start()] + f'exclude = [{inner2}]\n' + t[m.end():]
            changed = True
            return t2
        # Insert exclude right after [tool.ruff]
        t2 = re.sub(r'(\[tool\.ruff\]\s*\n)', r'\1exclude = ["vendor"]\n', t, count=1)
        if t2 != t:
            changed = True
        return t2

    def ensure_black(t: str) -> str:
        nonlocal changed
        if "[tool.black]" not in t:
            return t
        # Black uses extend-exclude regex, or exclude regex.
        if re.search(r'^\s*extend-exclude\s*=\s*.*vendor', t, flags=re.M) or re.search(r'^\s*exclude\s*=\s*.*vendor', t, flags=re.M):
            return t
        # Insert extend-exclude with vendor
        t2 = re.sub(r'(\[tool\.black\]\s*\n)', r"\1extend-exclude = '''(?x)(^vendor/.*$)'''\n", t, count=1)
        if t2 != t:
            changed = True
        return t2

    def ensure_isort(t: str) -> str:
        nonlocal changed
        if "[tool.isort]" not in t:
            return t
        if re.search(r'^\s*skip\s*=\s*.*vendor', t, flags=re.M) or re.search(r'^\s*skip_glob\s*=\s*.*vendor', t, flags=re.M):
            return t
        t2 = re.sub(r'(\[tool\.isort\]\s*\n)', r'\1skip = ["vendor"]\n', t, count=1)
        if t2 != t:
            changed = True
        return t2

    txt2 = txt
    txt2 = ensure_ruff(txt2)
    txt2 = ensure_black(txt2)
    txt2 = ensure_isort(txt2)

    if txt2 != txt:
        pyproject.write_text(txt2.replace("\r\n", "\n").replace("\r", "\n") + "\n", encoding="utf-8", newline="\n")
        return True
    return changed

def main() -> None:
    # 1) Lint excludes (best-effort, idempotent)
    patched = patch_pyproject_exclude_vendor(ROOT / "pyproject.toml")
    print(f"PYPROJECT_VENDOR_EXCLUDE_PATCHED={'YES' if patched else 'NO'}")

    # 2) Add negative tests for payload_sha256 required
    test_neg = r'''
from __future__ import annotations

from pathlib import Path
import pytest

from app.gui.planner import GuiStore, make_run_plan, persist_run_plan, make_approval, persist_approval, persist_handoff_from_plan
from app.validation.schema_validation import SchemaValidationError


def test_handoff_missing_sha_is_rejected(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)

    # Create a valid handoff record first (should pass)
    rec = persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")

    # Now mutate payload to remove sha and confirm schema rejects it
    import json
    obj = json.loads(rec.body)
    obj.pop("payload_sha256", None)

    from app.validation.schema_validation import validate_payload
    with pytest.raises(SchemaValidationError):
        validate_payload(obj)


def test_handoff_bad_sha_is_rejected(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)

    rec = persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")

    import json
    obj = json.loads(rec.body)
    obj["payload_sha256"] = "abc123"  # invalid length/pattern

    from app.validation.schema_validation import validate_payload
    with pytest.raises(SchemaValidationError):
        validate_payload(obj)
'''
    write(TESTS / "test_handoff_schema_negative.py", test_neg.strip("\n"))

    # 3) Cross-check: validate a GUI-produced handoff using the same resolver (already pinned)
    test_cross = r'''
from __future__ import annotations

from pathlib import Path
import json

from app.gui.planner import GuiStore, make_run_plan, persist_run_plan, make_approval, persist_approval, persist_handoff_from_plan
from app.validation.schema_validation import validate_payload


def test_gui_handoff_validates_under_vendor_schemas(tmp_path: Path) -> None:
    s = GuiStore(base_dir=tmp_path)

    plan = make_run_plan("T0001", "do thing", notes="n1")
    plan_rec = persist_run_plan(s, plan)

    appr = make_approval(plan_rec.ev_id, reviewer="Michael A. Trosen", decision="APPROVED", notes="ok")
    persist_approval(s, appr)

    rec = persist_handoff_from_plan(s, plan_rec, runner_label="TEST_RUNNER", notes="handoff note")

    payload = json.loads(rec.body)
    validate_payload(payload)  # must validate against vendor/swe-schemas pinned schema
'''
    write(TESTS / "test_gui_handoff_runner_parity.py", test_cross.strip("\n"))

    print("PHASE_2D_BUILD_WRITTEN=GREEN")

if __name__ == "__main__":
    main()
