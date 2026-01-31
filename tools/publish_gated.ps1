# Publish-Gated (canonical)
$ErrorActionPreference = "Stop"

function Gate([string]$name, [scriptblock]$body) {
  Write-Host ("=== GATE: {0} ===" -f $name)
  & $body
  if ($LASTEXITCODE -ne 0) { throw ("FAILURE DETECTED: gate failed: {0}" -f $name) }
  Write-Host ("{0}=GREEN" -f $name)
}

Gate "publish interlock set" {
  if ($env:SWENGINEER_ALLOW_PUBLISH -ne "1") {
    throw "FAILURE DETECTED: publish interlock is set. Set SWENGINEER_ALLOW_PUBLISH=1 to proceed."
  }
}

Gate "status clean (pre-publish)" {
  $s = & git status --porcelain
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: git status failed" }
  if ($s) { throw ("FAILURE DETECTED: working tree not clean:`n" + $s) }
}

Gate "pytest -q (pre-publish)" {
  python -m pytest -q
}

Gate "push branch + tag (already tagged)" {
  # SAFETY: refuse tag-only publish (must have a commit reachable from branch tip)
  $head = (& git rev-parse HEAD).Trim()
  if (-not $head) { throw "FAILURE DETECTED: could not resolve HEAD" }

  $tag = (& git describe --tags --exact-match).Trim()
  if (-not $tag) { throw "FAILURE DETECTED: HEAD must be exactly at a tag for this publish gate" }

  # Push current branch (must be on a branch)
  $branch = (& git rev-parse --abbrev-ref HEAD).Trim()
  if (-not $branch -or $branch -eq "HEAD") { throw "FAILURE DETECTED: detached HEAD; cannot push branch" }

  git push origin $branch
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: git push branch failed" }

  git push origin $tag
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: git push tag failed" }

  Write-Host ("PUBLISHED_TAG=" + $tag)
  Write-Host ("HEAD=" + $head)
  Write-Host ("BRANCH=" + $branch)
}
