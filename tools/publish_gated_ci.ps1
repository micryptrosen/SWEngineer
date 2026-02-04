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
$ci  = Join-Path $repo "tools\ci_pack.ps1"

if (-not (Test-Path -LiteralPath $pub)) { Fail ("FAILURE DETECTED: missing publish gate: " + $pub) 4 }
if (-not (Test-Path -LiteralPath $ci))  { Fail ("FAILURE DETECTED: missing ci_pack: " + $ci) 4 }

# 1) Run canonical publish gate first (authoritative)
& powershell -NoProfile -ExecutionPolicy Bypass -File $pub -Intent $Intent
$rc = $LASTEXITCODE
if ($rc -ne 0) { exit $rc }

# 2) Only if publish gate passed, run CI pack and emit pointer.
# Prevent nested pytest re-entry (ci_pack may run pytest unless explicitly skipped).
$env:SWENG_CI_PACK_SKIP_PYTEST = "1"

$txt = (& powershell -NoProfile -ExecutionPolicy Bypass -File $ci 2>&1 | Out-String)
$rc2 = $LASTEXITCODE
if ($rc2 -ne 0) {
  # Emit captured output for diagnostics while preserving rc.
  if ($txt) { Write-Host $txt }
  exit $rc2
}

# Keep output visible (useful for humans / logs) while still parsing it.
if ($txt) { Write-Host $txt }

$m = [regex]::Match($txt, 'CI_PACK_EVIDENCE_DIR=(.+)\r?$', [System.Text.RegularExpressions.RegexOptions]::Multiline)
if (-not $m.Success) { Fail "FAILURE DETECTED: CI_PACK_EVIDENCE_DIR not found in ci_pack output" 4 }

$ciDir = $m.Groups[1].Value.Trim()
Info ("PUBLISH_CI_PACK_DIR=" + $ciDir)
exit 0

