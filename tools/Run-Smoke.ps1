[CmdletBinding()]
param(
  [switch]$StrictWarnings,
  [switch]$SkipStatusClean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Gate([string]$Name, [scriptblock]$Body) {
  Write-Host ("=== GATE: {0} ===" -f $Name)
  & $Body
  if ($LASTEXITCODE -ne 0) { throw ("FAILURE DETECTED: gate failed: {0}" -f $Name) }
  Write-Host ("{0}=GREEN" -f $Name)
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Gate "pytest -q" {
  if ($StrictWarnings) {
    python -W error::DeprecationWarning -m pytest -q
  } else {
    python -m pytest -q
  }
}

Gate "isolated -I smoke (planner -> handoff -> validate)" {
  python -I tests\test_phase3_step3o_isolated_e2e_planner_handoff_validation.py
}

if (-not $SkipStatusClean) {
  Gate "status clean" {
    $s = git status --porcelain
    if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: git status failed" }
    if ($s) { throw ("FAILURE DETECTED: working tree not clean:`n" + $s) }
  }
}

Write-Host "SMOKE_OK=GREEN"

