param(
  [Parameter(Mandatory=$true, Position=0)]
  [ValidateNotNullOrEmpty()]
  [string]$Command,

  # PowerShell-native, avoids ambiguity with --out.
  [Parameter(Mandatory=$false)]
  [string]$Out = "",

  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Rest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $repo) { throw "FAILURE DETECTED: not in a git repo" }

$src = Join-Path $repo "src"
if (-not (Test-Path -LiteralPath $src)) { throw ("FAILURE DETECTED: missing src: " + $src) }

# Deterministic runs without installs: inject src/
$env:PYTHONPATH = $src

switch ($Command) {
  "parity-probe" {
    $pyArgs = @()
    if ($Out) { $pyArgs += @("--out", $Out) }
    if ($Rest) { $pyArgs += @($Rest) }

    python -c "import swengineer.cli_parity_probe as m; raise SystemExit(m.main())" @pyArgs
    exit $LASTEXITCODE
  }
  default {
    Write-Host "usage: .\tools\swengineer.ps1 parity-probe [-Out <path>] [args]"
    exit 2
  }
}

