from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase4b_ci_workflow_runs_publish_gate_harness() -> None:
    repo = _repo_root()
    wf = repo / ".github" / "workflows" / "ci.yml"
    assert wf.exists(), f"missing workflow: {wf}"

    txt = wf.read_text(encoding="utf-8")

    # CI must run an authoritative publish harness:
    # - tools/publish_gated.ps1 is canonical gate
    # - tools/publish_gated_ci.ps1 is thin wrapper around publish_gated + pointer emission
    has_publish_gate = "tools/publish_gated.ps1" in txt
    has_publish_ci = "tools/publish_gated_ci.ps1" in txt
    assert has_publish_gate or has_publish_ci, (
        "workflow must invoke tools/publish_gated.ps1 or tools/publish_gated_ci.ps1"
    )

    # Must set skip-pytest flags to avoid nested pytest re-entry / hangs.
    assert 'SWENG_PUBLISH_SKIP_PYTEST: "1"' in txt, "workflow must set SWENG_PUBLISH_SKIP_PYTEST=1"
    assert 'SWENG_CI_PACK_SKIP_PYTEST: "1"' in txt, "workflow must set SWENG_CI_PACK_SKIP_PYTEST=1"


