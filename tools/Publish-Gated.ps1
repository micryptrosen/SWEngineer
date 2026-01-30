param(
  [Parameter(Mandatory=$true)]
  [string]$Message,

  [Parameter(Mandatory=$true)]
  [string]$TagPrefix
)

$ErrorActionPreference = "Stop"

function Assert-LastExitCode([string]$what) {
  if ($LASTEXITCODE -ne 0) { throw ("FAILURE DETECTED: " + $what) }
}

function Gate([string]$name, [scriptblock]$body) {
  Write-Host ("=== GATE: {0} ===" -f $name)
  & $body
  Assert-LastExitCode ("gate failed: " + $name)
  Write-Host ("{0}=GREEN" -f $name)
}

Gate "status changed check (pre-publish)" {
  $s = & git status --porcelain
  Assert-LastExitCode "git status failed"
  if (-not $s) { throw "FAILURE DETECTED: no changes to commit (refusing tag-only publish)" }
}

Gate "publish-gated commit/tag/push" {
  & git add -A
  Assert-LastExitCode "git add failed"

  & git commit -m $Message
  Assert-LastExitCode "git commit failed"

  $tag = ("{0}_{1}" -f $TagPrefix, (Get-Date -Format "yyyyMMdd_HHmmss"))
  & git tag $tag
  Assert-LastExitCode "git tag failed"

  & git push
  Assert-LastExitCode "git push failed"

  & git push --tags
  Assert-LastExitCode "git push --tags failed"

  Write-Host ("PUBLISH=GREEN TAG={0}" -f $tag)
  Write-Host ("HEAD=" + (& git rev-parse HEAD))
  Write-Host ("ROOT=" + (Get-Location).Path)
}

Gate "status clean (post-push)" {
  $s = & git status --porcelain
  Assert-LastExitCode "git status failed"
  if ($s) { throw ("FAILURE DETECTED: working tree not clean:`n" + $s) }
}
