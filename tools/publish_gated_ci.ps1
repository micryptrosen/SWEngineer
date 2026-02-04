param(
  [Parameter(Mandatory=$true)][ValidateSet("tag","publish","noop")][string]$Intent
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Msg, [int]$Code = 4) {
  Write-Host $Msg
  exit $Code
}

function Info([string]$Msg) { Write-Host $Msg }

function RepoRoot() {
  $r = (& git rev-parse --show-toplevel 2>$null)
  if ($LASTEXITCODE -ne 0 -or -not $r) { Fail "FAILURE DETECTED: not a git repo (no toplevel)" 4 }
  return $r
}

$repo = RepoRoot
Set-Location -LiteralPath $repo

$pub = Join-Path $repo "tools\publish_gated.ps1"
if (-not (Test-Path -LiteralPath $pub)) { Fail ("FAILURE DETECTED: missing publish gate: " + $pub) 4 }

# Thin wrapper:
# - publish_gated.ps1 is authoritative and emits PUBLISH_CI_PACK_DIR on rc=0.
# - if publish gate refuses (rc!=0), propagate rc and emit nothing else.
# - ensure no nested pytest re-entry by default when called under pytest.
if ($env:PYTEST_CURRENT_TEST) { $env:SWENG_PUBLISH_SKIP_PYTEST = "1" }

$outLines = @()
& powershell -NoProfile -ExecutionPolicy Bypass -File $pub -Intent $Intent 2>&1 | ForEach-Object {
  $line = [string]$_
  $outLines += $line
  Write-Host $line
}
$rc = $LASTEXITCODE
if ($rc -ne 0) { exit $rc }

# On success: confirm pointer is present and surface it once (canonical line already printed).
$ptr = $null
foreach ($l in $outLines) {
  if ($l -match '^PUBLISH_CI_PACK_DIR=(.+)$') { $ptr = $Matches[1].Trim(); break }
}
if ([string]::IsNullOrWhiteSpace($ptr)) { Fail "FAILURE DETECTED: missing PUBLISH_CI_PACK_DIR in publish_gated output" 4 }

Info ("PUBLISH_CI_PACK_DIR=" + $ptr)
exit 0

