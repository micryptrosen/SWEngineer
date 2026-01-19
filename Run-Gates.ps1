$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location -LiteralPath "C:\Dev\CCP\SWEngineer"

$venv = Join-Path (Get-Location).Path ".venv"
$py = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $py)) {
  python -m venv $venv
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: venv creation failed (exit=$LASTEXITCODE)." }
}

& $py -m pip install -U pip | Out-Null
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: pip upgrade failed (exit=$LASTEXITCODE)." }

if (-not (Test-Path -LiteralPath "C:\Dev\CCP\SWEngineer\requirements.txt")) { throw "FAILURE DETECTED: missing C:\Dev\CCP\SWEngineer\requirements.txt" }
if (-not (Test-Path -LiteralPath "C:\Dev\CCP\SWEngineer\requirements-dev.txt")) { throw "FAILURE DETECTED: missing C:\Dev\CCP\SWEngineer\requirements-dev.txt" }

& $py -m pip install -r "C:\Dev\CCP\SWEngineer\requirements.txt" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: runtime deps install failed (exit=$LASTEXITCODE)." }

& $py -m pip install -r "C:\Dev\CCP\SWEngineer\requirements-dev.txt" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: dev deps install failed (exit=$LASTEXITCODE)." }

& $py "C:\Dev\CCP\SWEngineer\tools\gates.py" --mode local
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: gates.py failed (exit=$LASTEXITCODE)." }

Write-Host "GATES=GREEN SENTINEL=C:\Dev\CCP\SWEngineer\.gates\LAST_GREEN.txt"
