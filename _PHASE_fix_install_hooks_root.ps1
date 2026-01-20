$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$work = "C:\Dev\CCP\SWEngineer"
Set-Location -LiteralPath $work

function Log($msg) {
  $ts = (Get-Date).ToString("s")
  $line = "$ts $msg"
  Write-Host $line
  Add-Content -LiteralPath "C:\Dev\CCP\SWEngineer\_PHASE_fix_install_hooks_root.log" -Encoding UTF8 -Value $line
}

try {
  Log "=== FIX — Install-Hooks firewall v3: define repo root locally ==="

  $py = "C:\Dev\CCP\SWEngineer\.venv\Scripts\python.exe"
  if (-not (Test-Path -LiteralPath $py)) { throw "FAILURE DETECTED: missing venv python at $py" }

  & $py -c 'from __future__ import annotations
import re
from pathlib import Path

p = Path(r"C:\Dev\CCP\SWEngineer\tools\Install-Hooks.ps1")
s = p.read_text(encoding="utf-8")

if "FIREWALL_V3_ROOT_RESOLVE" in s:
    print("NOOP=root resolve already patched")
else:
    needle = r"$hooks = Join-Path $root "".git\hooks"""
    if needle not in s:
        raise SystemExit("FAILURE DETECTED: expected hooks line not found; aborting patch (file structure drift).")

    repl = (
        "# FIREWALL_V3_ROOT_RESOLVE\n"
        "$fwRoot = (git rev-parse --show-toplevel).Trim()\n"
        "if (-not $fwRoot) { throw \"FAILURE DETECTED: unable to resolve repo root\" }\n"
        "$hooks = Join-Path $fwRoot \".git\\hooks\"\n"
    )

    s = s.replace(needle, repl, 1)
    p.write_text(s, encoding="utf-8", newline="\n")
    print("PATCHED=tools/Install-Hooks.ps1 (root resolve)")
'
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: patch failed (exit=$LASTEXITCODE)." }

  Log "=== RE-RUN Install-Hooks (should succeed) ==="
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Dev\CCP\SWEngineer\tools\Install-Hooks.ps1"
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: Install-Hooks failed (exit=$LASTEXITCODE)." }

  Log "=== GATES (GREEN OR STOP) ==="
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Dev\CCP\SWEngineer\Run-Gates.ps1"
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: gates failed (exit=$LASTEXITCODE)." }

  Log "=== COMMIT + PUSH (GREEN ONLY) ==="
  git add -A
  $staged = git diff --cached --name-only
  if (-not $staged) { Log "NOTE: nothing staged. PUBLISH=GREEN"; exit 0 }

  git commit -m "fix: install-hooks firewall v3 resolves repo root locally"
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: git commit failed (exit=$LASTEXITCODE)." }

  git push
  if ($LASTEXITCODE -ne 0) { throw "FAILURE DETECTED: git push failed (exit=$LASTEXITCODE)." }

  Log "PUBLISH=GREEN"
}
catch {
  Log ("FAILURE DETECTED: " + $_.Exception.Message)
  Log "STACK:"
  Log $_.ScriptStackTrace
  Write-Host ""
  Write-Host ("LOG_FILE=C:\Dev\CCP\SWEngineer\_PHASE_fix_install_hooks_root.log")
  Read-Host "PAUSED (press Enter) — so the window cannot close on you"
  exit 1
}
