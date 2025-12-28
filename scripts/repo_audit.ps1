# File: C:\Dev\CCP\SWEngineer\scripts\repo_audit.ps1
[CmdletBinding()]
param(
  [Parameter()]
  [string]$Root = "",

  [Parameter()]
  [int]$MaxTrackedMB = 25,

  [Parameter()]
  [int]$MaxUntrackedMB = 200
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Fail([string]$Msg) {
  Write-Host "FAIL: $Msg"
  exit 1
}

function Warn([string]$Msg) {
  Write-Host "WARN: $Msg"
}

function Info([string]$Msg) {
  Write-Host "INFO: $Msg"
}

if ([string]::IsNullOrWhiteSpace($Root)) {
  $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
  $Root = (Resolve-Path $Root).Path
}

Set-Location $Root

if (-not (Test-Path (Join-Path $Root ".git"))) {
  Fail "Not a git repository: $Root"
}

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
  Fail "git not found on PATH"
}

Info "Root: $Root"
Info "MaxTrackedMB: $MaxTrackedMB"
Info "MaxUntrackedMB: $MaxUntrackedMB"

# 1) Ensure we are on a branch
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -eq "HEAD") {
  Fail "Detached HEAD"
}
Info "Branch: $branch"

# 2) Verify ignored directories not tracked
$trackedVenv = (git ls-files ".venv/*" 2>$null)
if ($trackedVenv) {
  Fail ".venv is tracked. Remove it from git history."
}

# 3) Find suspicious tracked filenames (e.g. '6.7')
$tracked = git ls-files
foreach ($f in $tracked) {
  if ($f -match '(^|/)\d+(\.\d+)?$') {
    Warn "Suspicious tracked filename: $f"
  }
}

# 4) Block known-bad tracked extensions
$badTrackedExt = @(".whl", ".tar.gz", ".zip", ".7z", ".rar", ".exe", ".dll")
foreach ($f in $tracked) {
  foreach ($ext in $badTrackedExt) {
    if ($f.ToLowerInvariant().EndsWith($ext)) {
      Fail "Tracked forbidden artifact: $f"
    }
  }
}

# 5) Large tracked files in current tree
$maxTrackedBytes = $MaxTrackedMB * 1024 * 1024
$largeTracked = @()

foreach ($f in $tracked) {
  $p = Join-Path $Root $f
  if (Test-Path $p) {
    try {
      $len = (Get-Item $p).Length
      if ($len -gt $maxTrackedBytes) {
        $largeTracked += [pscustomobject]@{ Path = $f; SizeMB = [math]::Round($len / 1MB, 2) }
      }
    } catch {}
  }
}

if ($largeTracked.Count -gt 0) {
  Write-Host ""
  Write-Host "Large tracked files:"
  $largeTracked | Sort-Object SizeMB -Descending | Format-Table -AutoSize | Out-String | Write-Host
  Fail "Tracked file(s) exceed MaxTrackedMB"
}

# 6) Large untracked files (warn)
$maxUntrackedBytes = $MaxUntrackedMB * 1024 * 1024
$untracked = git ls-files --others --exclude-standard
$largeUntracked = @()

foreach ($f in $untracked) {
  $p = Join-Path $Root $f
  if (Test-Path $p) {
    try {
      $len = (Get-Item $p).Length
      if ($len -gt $maxUntrackedBytes) {
        $largeUntracked += [pscustomobject]@{ Path = $f; SizeMB = [math]::Round($len / 1MB, 2) }
      }
    } catch {}
  }
}

if ($largeUntracked.Count -gt 0) {
  Write-Host ""
  Write-Host "Large untracked files:"
  $largeUntracked | Sort-Object SizeMB -Descending | Format-Table -AutoSize | Out-String | Write-Host
  Warn "Untracked large file(s) detected (not failing)."
}

# 7) Quick repo cleanliness summary
$porcelain = git status --porcelain
if ($porcelain) {
  Warn "Working tree has changes."
} else {
  Info "Working tree clean."
}

Write-Host "OK"
exit 0
