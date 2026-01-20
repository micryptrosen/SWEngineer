$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) { throw "FAILURE DETECTED: missing venv python at $py (create venv first)." }

$gatesDir = Join-Path $root ".gates"
New-Item -ItemType Directory -Path $gatesDir -Force | Out-Null

Write-Host "=== GATES (tools/gates.py) ==="
& $py (Join-Path $root "tools\gates.py") --mode local
if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: gates.py failed (exit=$LASTEXITCODE)." }

# Mint HEAD-bound sentinel (runtime-only; .gates is gitignored)
$head = (git rev-parse HEAD).Trim()
$sent = Join-Path $gatesDir "LAST_GREEN.txt"
Set-Content -LiteralPath $sent -Encoding UTF8 -Value ("HEAD=" + $head + "`n")
Write-Host ("SENTINEL_HEAD=" + $head)
Write-Host ("GATES=GREEN SENTINEL=" + $sent)
