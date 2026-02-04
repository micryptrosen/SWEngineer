from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase4b_ci_workflow_runs_publish_gate_harness() -> None:
    repo = _repo_root()
    wf = repo / ".github" / "workflows" / "ci.yml"
    assert wf.exists(), f"missing workflow: {wf}"

    txt = wf.read_text(encoding="utf-8")

    # Must run canonical publish gate harness in CI.
    assert "tools/publish_gated.ps1" in txt, "workflow must invoke tools/publish_gated.ps1"
    assert "-Intent tag" in txt, "workflow must run publish gate with -Intent tag"
    assert "SWENG_PUBLISH_SKIP_PYTEST" in txt, "workflow must set SWENG_PUBLISH_SKIP_PYTEST to avoid duplicate pytest"


