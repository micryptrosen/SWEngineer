from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _run(argv: list[str], *, cwd: Path) -> None:
    p = subprocess.run(argv, cwd=str(cwd))
    if p.returncode != 0:
        raise SystemExit(f"FAILURE DETECTED: gate failed: {' '.join(argv)} (exit={p.returncode}).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["local", "ci"], required=True)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    os.chdir(root)

    py = sys.executable

    # Compile (fast sanity)
    _run([py, "-m", "compileall", "-q", "."], cwd=root)

    # Format / style
    if args.mode == "local":
        # Auto-format locally; CI will verify.
        _run([py, "-m", "black", "."], cwd=root)
    else:
        _run([py, "-m", "black", "--check", "."], cwd=root)

    # Lint
    _run([py, "-m", "ruff", "check", "."], cwd=root)

    # CI workflow sanity (if validator exists)
    v = root / "tools" / "validate_ci.py"
    if v.exists():
        _run([py, str(v)], cwd=root)
    # Tests (must run; smoke test exists)
    _run([py, "-m", "pytest", "-q"], cwd=root)

    # Mint commit-firewall sentinel only for local runs
    if args.mode == "local":
        gates_dir = root / ".gates"
        gates_dir.mkdir(parents=True, exist_ok=True)
        (gates_dir / "LAST_GREEN.txt").write_text("GREEN\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
