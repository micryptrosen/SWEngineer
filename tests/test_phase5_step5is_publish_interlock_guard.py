from pathlib import Path

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def test_publish_gated_has_interlock_guard() -> None:
    root = _repo_root()
    p = root / "tools" / "Publish-Gated.ps1"
    assert p.exists(), "tools/Publish-Gated.ps1 missing"
    txt = p.read_text(encoding="utf-8", errors="ignore")
    assert "SWENGINEER_ALLOW_PUBLISH" in txt, "publish interlock guard missing"
