# File: C:\Dev\CCP\SWEngineer\README.md

# SWEngineer (LocalAISWE)

Local AI Software Engineer (Windows 11) — GUI + local engine runtime (in progress).

## Requirements
- Windows 11
- Python 3.11+
- PowerShell
- (Optional) GitHub CLI: `gh`

## Project root
This repo is designed to run from:
`C:\Dev\CCP\SWEngineer`

## Setup (first time)
Run this in PowerShell:

```powershell
cd C:\Dev\CCP\SWEngineer
powershell -NoProfile -ExecutionPolicy Bypass -File .\towershell.ps1 init
powershell -NoProfile -ExecutionPolicy Bypass -File .\towershell.ps1 install
