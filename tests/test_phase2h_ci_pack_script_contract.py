from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase2h_ci_pack_script_contract() -> None:
    repo = _repo_root()
    p = repo / "tools" / "ci_pack.ps1"
    assert p.exists(), f"missing ci_pack.ps1: {p}"
    txt = p.read_text(encoding="utf-8")
    assert "python -m pytest -q" in txt
    assert "parity-probe" in txt
    assert "CI_PACK_EVIDENCE_DIR=" in txt
    assert "CI_PACK=GREEN" in txt

