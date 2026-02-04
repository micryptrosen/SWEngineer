from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase4a_github_actions_ci_workflow_present_and_minimal_contract() -> None:
    repo = _repo_root()
    wf = repo / ".github" / "workflows" / "ci.yml"
    assert wf.exists(), f"missing workflow: {wf}"

    txt = wf.read_text(encoding="utf-8")
    must = [
        "name: CI",
        "pull_request",
        "push",
        "runs-on: windows-latest",
        "actions/checkout@v4",
        "actions/setup-python@v5",
        'python-version: "3.12"',
        "python -m pytest -q",
    ]
    missing = [m for m in must if m not in txt]
    assert not missing, f"workflow missing tokens: {missing}\n---\n{txt}\n---"

