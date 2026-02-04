from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase2e_publish_gate_requires_parity_probe() -> None:
    repo = _repo_root()
    p = repo / "tools" / "publish_gated.ps1"
    assert p.exists(), f"missing publish gate: {p}"
    txt = p.read_text(encoding="utf-8")

    assert "tools\\swengineer.ps1" in txt or "tools/swengineer.ps1" in txt
    assert "parity-probe" in txt

    # Phase2G contract: use PowerShell-native -Out evidence path (avoid --out ambiguity)
    assert "-Out" in txt
    assert "--out" not in txt

