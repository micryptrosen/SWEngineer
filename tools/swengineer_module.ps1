param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Rest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path -LiteralPath (Join-Path -Path $PSScriptRoot -ChildPath "..")).Path
$src  = (Resolve-Path -LiteralPath (Join-Path -Path $repo -ChildPath "src")).Path

# Ensure src is importable for the child python process (without requiring install).
if ($env:PYTHONPATH) {
  $env:PYTHONPATH = ($src + ";" + $env:PYTHONPATH)
} else {
  $env:PYTHONPATH = $src
}

$py = $env:PYTHON
if (-not $py) { $py = "python" }

& $py "-m" "swengineer" @Rest
exit $LASTEXITCODE

