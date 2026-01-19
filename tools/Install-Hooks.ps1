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
