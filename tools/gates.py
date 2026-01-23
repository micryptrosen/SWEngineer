from __future__ import annotations

import argparse
import subprocess
import sys


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, text=True)
    if p.returncode != 0:
        raise SystemExit(f"FAILURE DETECTED: gate failed: {' '.join(cmd)} (exit={p.returncode}).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["local", "ci"])
    ap.parse_args()

    # Tooling
    run([sys.executable, "-m", "pip", "install", "-U", "pip"])
    run([sys.executable, "-m", "pip", "install", "black", "ruff", "pytest"])

    # IMPORTANT: exclude vendor/ (git submodules live there)
    run([sys.executable, "-m", "black", "--exclude", r"(^|/|\\)vendor(/|\\)", "."])
    run([sys.executable, "-m", "ruff", "check", "--exclude", "vendor", "."])
    run([sys.executable, "-m", "pytest", "-q"])

    print("GATES=GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
