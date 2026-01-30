param(
  [Parameter(Mandatory=$true)]
  [string]$Message,

  [Parameter(Mandatory=$true)]
  [string]$TagPrefix
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-LastExitCode([string]$what) {
  if ($LASTEXITCODE -ne 0) { throw ("FAILURE DETECTED: " + $what) }
}

# -------------------------------------------------------------------
# PUBLISH INTERLOCK (Phase5/Step5IT)
# This wrapper MUST NOT publish unless explicitly armed for the session.
# -------------------------------------------------------------------
if ($env:SWENGINEER_ALLOW_PUBLISH -ne "YES") {
  throw "FAILURE DETECTED: publish interlock not armed. Set `$env:SWENGINEER_ALLOW_PUBLISH='YES'` for this session to enable publish."
}

# 1) sanity: must have changes (prevents tag-only publish)
$s = & git status --porcelain
Assert-LastExitCode "git status failed"
if (-not $s) { throw "FAILURE DETECTED: no changes to commit (refusing tag-only publish)" }

# 2) stage all
& git add -A
Assert-LastExitCode "git add failed"

# 3) commit
& git commit -m $Message
Assert-LastExitCode "git commit failed"

# 4) tag
$tag = ($TagPrefix)
& git tag $tag
Assert-LastExitCode "git tag failed"

# 5) push commit + tags
& git push
Assert-LastExitCode "git push failed"

& git push --tags
Assert-LastExitCode "git push --tags failed"

Write-Host ("PUBLISH=GREEN TAG={0}" -f $tag)
Write-Host ("HEAD=" + (& git rev-parse HEAD))
Write-Host "ROOT=C:\Dev\CCP\SWEngineer"

# 6) post: working tree clean
$s2 = & git status --porcelain
Assert-LastExitCode "git status failed"
if ($s2) { throw ("FAILURE DETECTED: working tree not clean:`n" + $s2) }
