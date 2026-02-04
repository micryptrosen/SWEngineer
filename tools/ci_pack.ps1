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

function Sha256File([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { Fail ("FAILURE DETECTED: missing file for sha256: " + $Path) 4 }
  $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
  $name = [IO.Path]::GetFileName($Path)
  $side = ($Path + ".sha256")
  Set-Content -LiteralPath $side -Value ($hash + "  " + $name + "`n") -Encoding UTF8 -NoNewline
}

function CopyStrict([string]$Src, [string]$Dst) {
  if (-not (Test-Path -LiteralPath $Src)) { Fail ("FAILURE DETECTED: missing required artifact: " + $Src) 4 }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dst) | Out-Null
  Copy-Item -LiteralPath $Src -Destination $Dst -Force
}

$repo = RepoRoot
Set-Location -LiteralPath $repo

$ts = (Get-Date).ToString("yyyyMMdd_HHmmss")
$bundleRoot = Join-Path $repo ("_evidence\ci_pack\" + $ts)
New-Item -ItemType Directory -Force -Path $bundleRoot | Out-Null

# CONTRACT TOKENS (Phase2H): do not remove.
Info ("CI_PACK_EVIDENCE_DIR=" + $bundleRoot)

# 1) pytest unless skipped (avoid nested pytest deadlocks under pytest)
$skipPytest = [string]$env:SWENG_CI_PACK_SKIP_PYTEST
if ($skipPytest -and $skipPytest.Trim().ToLowerInvariant() -eq "1") {
  Info "CI_PACK: pytest=SKIPPED (SWENG_CI_PACK_SKIP_PYTEST=1)"
} else {
  Info "CI_PACK: running pytest"
  python -m pytest -q
  if ($LASTEXITCODE -ne 0) { Fail ("FAILURE DETECTED: pytest rc=" + $LASTEXITCODE) 4 }
  Info "CI_PACK: pytest=GREEN"
}

# 2) parity-probe evidence (fresh) into bundle
$parityOut = Join-Path $bundleRoot "parity_probe.json"
Info ("CI_PACK: writing parity-probe to " + $parityOut)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\swengineer.ps1") parity-probe -Out $parityOut | Out-Null
$rc = $LASTEXITCODE
if ($rc -ne 0 -and $rc -ne 2) { Fail ("FAILURE DETECTED: parity-probe rc=" + $rc) 4 }
if (-not (Test-Path -LiteralPath $parityOut)) { Fail ("FAILURE DETECTED: parity-probe out missing: " + $parityOut) 4 }
if (-not (Test-Path -LiteralPath ($parityOut + ".sha256"))) { Fail ("FAILURE DETECTED: parity-probe sha256 missing: " + $parityOut + ".sha256") 4 }
Info "CI_PACK: parity-probe=OK"

# 3) Include publish parity-probe evidence if it exists
$publishDir = Join-Path $repo "_evidence\publish"
$publishParity = Join-Path $publishDir "parity_probe.json"
$publishParitySha = ($publishParity + ".sha256")

if (Test-Path -LiteralPath $publishParity) {
  Info "CI_PACK: bundling publish parity-probe evidence"
  if (-not (Test-Path -LiteralPath $publishParitySha)) {
    Sha256File $publishParity
  }
  CopyStrict $publishParity (Join-Path $bundleRoot "publish\parity_probe.json")
  CopyStrict $publishParitySha (Join-Path $bundleRoot "publish\parity_probe.json.sha256")
} else {
  Info "CI_PACK: no _evidence\publish\parity_probe.json present (ok)"
}

# CONTRACT TOKEN (Phase2H): do not remove.
Info "CI_PACK=GREEN"
exit 0

