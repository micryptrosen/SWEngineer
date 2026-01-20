$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve repo root robustly (do NOT rely on caller scope)
$root = (git rev-parse --show-toplevel).Trim()
if (-not $root) { throw "FAILURE DETECTED: unable to resolve repo root (git rev-parse failed)" }
Set-Location -LiteralPath $root

$hookSrc = Join-Path $root "tools\hooks\pre-commit"
if (-not (Test-Path -LiteralPath $hookSrc)) { throw "FAILURE DETECTED: missing $hookSrc" }

$hookDir = Join-Path $root ".git\hooks"
if (-not (Test-Path -LiteralPath $hookDir)) { throw "FAILURE DETECTED: missing $hookDir (not a git repo?)" }

# Keep legacy bash hook removed (we are Windows-hook only)
$bashHook = Join-Path $hookDir "pre-commit"
if (Test-Path -LiteralPath $bashHook) { Remove-Item -Force -LiteralPath $bashHook }

# Install Windows hook (PowerShell + CMD shim)
$psHook = Join-Path $hookDir "pre-commit.ps1"
$cmdHook = Join-Path $hookDir "pre-commit.cmd"

Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $psHook
Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $cmdHook

Add-Content -LiteralPath $psHook -Encoding UTF8 -Value '$ErrorActionPreference = "Stop"'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value 'Set-StrictMode -Version Latest'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value ''
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value '$root = (git rev-parse --show-toplevel).Trim()'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value 'if (-not $root) { Write-Host "FAILURE DETECTED: unable to resolve repo root"; exit 1 }'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value 'Set-Location -LiteralPath $root'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value ''
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value '$rg = Join-Path $root "Run-Gates.ps1"'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value 'if (-not (Test-Path -LiteralPath $rg)) { Write-Host "FAILURE DETECTED: missing Run-Gates.ps1"; exit 1 }'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value ''
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value 'powershell -NoProfile -ExecutionPolicy Bypass -File $rg'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value '$rc = $LASTEXITCODE'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value 'if ($rc -ne 0) { Write-Host ("FAILURE DETECTED: gates are RED (exit=" + $rc + "). Commit blocked."); exit $rc }'
Add-Content -LiteralPath $psHook -Encoding UTF8 -Value 'exit 0'

Add-Content -LiteralPath $cmdHook -Encoding ASCII -Value '@echo off'
Add-Content -LiteralPath $cmdHook -Encoding ASCII -Value 'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pre-commit.ps1"'
Add-Content -LiteralPath $cmdHook -Encoding ASCII -Value 'exit /b %ERRORLEVEL%'

Write-Host "HOOK_INSTALLED=$psHook ; $cmdHook"
Write-Host "NEXT: run gates once to mint sentinel:"
Write-Host ("powershell -NoProfile -ExecutionPolicy Bypass -File `"" + (Join-Path $root "Run-Gates.ps1") + "`"")
