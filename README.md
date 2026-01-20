# SWEngineer

Local "Nova-in-a-box" style software engineer assistant (GUI-first) with deterministic gates.

## Python
- Required: Python 3.12+ (repo is locked to 3.12 in CI)

## Quickstart (Windows)
Commands:
1) Set-Location -LiteralPath "C:\Dev\CCP\SWEngineer"
2) powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Install-Hooks.ps1
3) powershell -NoProfile -ExecutionPolicy Bypass -File .\Run-Gates.ps1

## Gates (single source of truth)
 - tools/gates.py is authoritative.
 - Local: powershell -NoProfile -ExecutionPolicy Bypass -File .\Run-Gates.ps1
 - CI: python tools/gates.py --mode ci

## Commit Firewall
Commits are blocked unless ".gates/LAST_GREEN.txt" exists (minted by running gates).
