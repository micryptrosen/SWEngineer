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

& $py -m pip install -r "C:\Dev\CCP\SWEngineer\requirements.txt" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: runtime deps install failed (exit=$LASTEXITCODE)." }

& $py -m pip install -r "C:\Dev\CCP\SWEngineer\requirements-dev.txt" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: dev deps install failed (exit=$LASTEXITCODE)." }

& $py -m compileall -q .
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: compileall gate is RED (exit=$LASTEXITCODE)." }

& $py -m black .
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: black format failed (exit=$LASTEXITCODE)." }

& $py -m ruff check .
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: ruff gate is RED (exit=$LASTEXITCODE)." }

& $py -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: pytest gate is RED (exit=$LASTEXITCODE)." }

New-Item -ItemType Directory -Force -Path ".gates" | Out-Null
"GREEN " + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") | Set-Content -LiteralPath ".gates\LAST_GREEN.txt" -Encoding UTF8

Write-Host "GATES=GREEN SENTINEL=.gates\LAST_GREEN.txt"
