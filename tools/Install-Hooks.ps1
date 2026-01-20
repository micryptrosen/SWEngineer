$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$work = "C:\Dev\CCP\SWEngineer"
Set-Location -LiteralPath $work

$hookSrc = Join-Path $work "tools\hooks\pre-commit"
if (-not (Test-Path -LiteralPath $hookSrc)) { throw "FAILURE DETECTED: missing $hookSrc" }

$hookDir = Join-Path $work ".git\hooks"
if (-not (Test-Path -LiteralPath $hookDir)) { throw "FAILURE DETECTED: missing $hookDir (not a git repo?)" }

$hookDst = Join-Path $hookDir "pre-commit"
Copy-Item -Force -LiteralPath $hookSrc -Destination $hookDst

Write-Host "HOOK_INSTALLED=$hookDst"
Write-Host "NEXT: run gates once to mint sentinel:"
Write-Host "powershell -NoProfile -ExecutionPolicy Bypass -File `"$work\Run-Gates.ps1`""

### COMMIT FIREWALL v3 (auto-run gates)
$hooks = Join-Path $root ".git\hooks"
if (-not (Test-Path -LiteralPath $hooks)) { throw "FAILURE DETECTED: missing .git\hooks (are you in a git repo?)." }

# --- COMMIT FIREWALL v3 (auto-run gates) ---
# Git for Windows executes hooks via sh; write a sh hook with LF newlines.
$hook = Join-Path $hooks "pre-commit"

$lines = @(
"#!/bin/sh",
"set -eu",
"ROOT=`"`$(git rev-parse --show-toplevel)`"",
"POWERSHELL_EXE=`"powershell.exe`"",
"`"$POWERSHELL_EXE`" -NoProfile -ExecutionPolicy Bypass -File `"$ROOT/Run-Gates.ps1`"",
"rc=$?",
"if [ `"$rc`" -ne 0 ]; then",
"  echo `"FAILURE DETECTED: gates are RED (exit=$rc). Commit blocked.`"",
"  exit `"$rc`"",
"fi",
"exit 0"
) -join "`n"

[System.IO.File]::WriteAllBytes($hook, [System.Text.Encoding]::UTF8.GetBytes($lines + "`n"))
Write-Host "HOOK_INSTALLED=$hook"
