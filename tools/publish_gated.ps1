param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("tag","publish")]
  [string]$Intent
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Msg, [int]$Code = 4) {
  Write-Host $Msg
  exit $Code
}

function Info([string]$Msg) { Write-Host $Msg }

function Gate {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][scriptblock]$Body
  )
  Write-Host "`n=== GATE: $Name ==="
  $global:LASTEXITCODE = 0
  & $Body
  if ($LASTEXITCODE -ne 0) { Fail ("FAILURE DETECTED: gate '" + $Name + "' rc=" + $LASTEXITCODE) 4 }
  Write-Host ("GATE=GREEN NAME=" + $Name)
}

function RepoRoot() {
  $r = (& git rev-parse --show-toplevel 2>$null)
  if ($LASTEXITCODE -ne 0 -or -not $r) { Fail "FAILURE DETECTED: not a git repo (no toplevel)" 4 }
  return $r
}

$repo = RepoRoot
Set-Location -LiteralPath $repo

$evidenceDir = Join-Path $repo "_evidence\publish"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

$parityJson = Join-Path $evidenceDir "parity_probe.json"

Gate "preflight: git clean working tree (enforced)" {
  $dirty = (& git status --porcelain)
  if ($dirty) { Fail "FAILURE DETECTED: dirty working tree. publish gate requires clean tree." 4 }
}

Gate "pytest (must be green)" {
  if ($env:PYTEST_CURRENT_TEST) {
    Info "PYTEST_SKIP_NESTED=1"
    return
  }
  python -m pytest -q
}

Gate "parity-probe evidence (required)" {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\swengineer.ps1") parity-probe -Out $parityJson | Out-Null
  $rc = $LASTEXITCODE
  if ($rc -ne 0 -and $rc -ne 2) { Fail ("FAILURE DETECTED: parity-probe rc=" + $rc) 4 }
  if (-not (Test-Path -LiteralPath $parityJson)) { Fail ("FAILURE DETECTED: parity-probe out missing: " + $parityJson) 4 }
  if (-not (Test-Path -LiteralPath ($parityJson + ".sha256"))) { Fail ("FAILURE DETECTED: parity-probe sha256 missing: " + $parityJson + ".sha256") 4 }
}

Gate "parity-probe selection matches snapshot (if present)" {
  $snap = Join-Path $repo "tests\_snapshots\phase3c_selection.json"
  if (Test-Path -LiteralPath $snap) {
    $snapObj = Get-Content -LiteralPath $snap -Raw | ConvertFrom-Json
    $probeObj = Get-Content -LiteralPath $parityJson -Raw | ConvertFrom-Json

    if ($null -eq $probeObj.selection) { Fail "FAILURE DETECTED: parity-probe selection block missing" 4 }

    $runnerA = [string]$probeObj.selection.runner_mod
    $surfaceA = [string]$probeObj.selection.surface_mod
    $runnerE = [string]$snapObj.runner_mod
    $surfaceE = [string]$snapObj.surface_mod

    if ([string]::IsNullOrWhiteSpace($runnerA) -or [string]::IsNullOrWhiteSpace($surfaceA)) {
      Fail "FAILURE DETECTED: parity-probe selection fields missing" 4
    }

    if ($runnerA -ne $runnerE) { Fail ("FAILURE DETECTED: runner selection drift: got=" + $runnerA + " expected=" + $runnerE) 4 }
    if ($surfaceA -ne $surfaceE) { Fail ("FAILURE DETECTED: surface selection drift: got=" + $surfaceA + " expected=" + $surfaceE) 4 }
  }
}

Gate "intent: explicit publish intent" {
  if ($Intent -ne "tag" -and $Intent -ne "publish") { Fail "FAILURE DETECTED: invalid intent" 4 }
  Info ("INTENT=" + $Intent)
}

Gate "ci-pack evidence (post-success)" {
  $env:SWENG_CI_PACK_SKIP_PYTEST = "1"

  $ciPackScript = Join-Path $repo "tools\ci_pack.ps1"
  if (-not (Test-Path -LiteralPath $ciPackScript)) { Fail ("FAILURE DETECTED: ci_pack.ps1 missing: " + $ciPackScript) 4 }

  $outLines = @()
  & powershell -NoProfile -ExecutionPolicy Bypass -File $ciPackScript 2>&1 | ForEach-Object {
    $line = [string]$_
    $outLines += $line
    Write-Host $line
  }
  $rc = $LASTEXITCODE
  if ($rc -ne 0) { Fail ("FAILURE DETECTED: ci_pack rc=" + $rc) 4 }

  $ciEvidence = $null
  foreach ($l in $outLines) {
    if ($l -match '^CI_PACK_EVIDENCE_DIR=(.+)$') { $ciEvidence = $Matches[1].Trim(); break }
  }
  if ([string]::IsNullOrWhiteSpace($ciEvidence)) { Fail "FAILURE DETECTED: CI_PACK_EVIDENCE_DIR missing from ci_pack output" 4 }

  Info ("PUBLISH_CI_PACK_DIR=" + $ciEvidence)
}

Info "PUBLISH_GATED=GREEN"
exit 0

