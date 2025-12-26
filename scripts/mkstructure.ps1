# File: C:\Dev\CCP\SWEngineer\towershell.ps1
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet("help", "init", "install", "run", "verify", "test", "format", "lint", "build")]
  [string]$Action = "help",

  [Parameter(Position = 1)]
  [string]$Arg1 = "",

  [Parameter(Position = 2)]
  [string]$Arg2 = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Section([string]$Text) {
  Write-Host ""
  Write-Host "== $Text =="
}

function Resolve-ProjectRoot {
  return (Get-Location).Path
}

function Get-PythonCmd {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return "python" }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return "py -3" }

  throw "Python not found. Install Python 3.11+ and ensure it's on PATH."
}

function Invoke-External([string]$CmdLine) {
  Write-Host "> $CmdLine"
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "cmd.exe"
  $psi.Arguments = "/c $CmdLine"
  $psi.RedirectStandardOutput = $false
  $psi.RedirectStandardError = $false
  $psi.UseShellExecute = $true

  $p = [System.Diagnostics.Process]::Start($psi)
  $p.WaitForExit()
  if ($p.ExitCode -ne 0) { throw "Command failed with exit code $($p.ExitCode): $CmdLine" }
}

function Ensure-Dirs {
  $root = Resolve-ProjectRoot

  $dirs = @(
    ".vscode",
    "app",
    "app\core",
    "app\core\services",
    "app\core\types",
    "app\engine",
    "app\engine\tools",
    "app\engine\providers",
    "app\engine\runtime",
    "app\gui",
    "app\gui\widgets",
    "app\gui\assets",
    "app\resources",
    "app\resources\icons",
    "app\resources\themes",
    "data",
    "data\models",
    "data\prompts",
    "data\sessions",
    "data\telemetry",
    "docs",
    "scripts",
    "tests",
    "tests\unit",
    "tests\integration",
    "dist",
    "build",
    "logs",
    "tmp"
  )

  foreach ($d in $dirs) {
    $p = Join-Path $root $d
    if (-not (Test-Path $p)) {
      New-Item -ItemType Directory -Path $p | Out-Null
    }
  }
}

function Ensure-Venv {
  $root = Resolve-ProjectRoot
  $venv = Join-Path $root ".venv"
  if (Test-Path $venv) { return }

  Write-Section "Creating venv (.venv)"
  $py = Get-PythonCmd
  Invoke-External "$py -m venv .venv"
}

function Get-VenvPython {
  $root = Resolve-ProjectRoot
  $venvPy = Join-Path $root ".venv\Scripts\python.exe"
  if (-not (Test-Path $venvPy)) { throw "Missing venv python at $venvPy. Run: .\towershell.ps1 init" }
  return $venvPy
}

function Pip-InstallBase {
  $venvPy = Get-VenvPython
  Write-Section "Installing dependencies"
  Invoke-External "`"$venvPy`" -m pip install --upgrade pip wheel setuptools"

  $req = "requirements.txt"
  if (Test-Path $req) {
    Invoke-External "`"$venvPy`" -m pip install -r requirements.txt"
    return
  }

  $pkgs = @(
    "pyside6>=6.7",
    "pydantic>=2.7",
    "httpx>=0.27",
    "rich>=13.7",
    "pytest>=8.2",
    "ruff>=0.6",
    "black>=24.4",
    "mypy>=1.10",
    "pyinstaller>=6.7"
  )
  Invoke-External "`"$venvPy`" -m pip install $($pkgs -join ' ')"
}

function Action-Help {
@"
towershell.ps1 (Windows PowerShell)

Usage:
  .\towershell.ps1 init
  .\towershell.ps1 install
  .\towershell.ps1 run
  .\towershell.ps1 verify <path-to-file>
  .\towershell.ps1 test
  .\towershell.ps1 format
  .\towershell.ps1 lint
  .\towershell.ps1 build
"@ | Write-Host
}

function Action-Init {
  Write-Section "Initializing project scaffold"
  Ensure-Dirs
  Ensure-Venv
  Write-Host "OK"
  Write-Host "Next: powershell -ExecutionPolicy Bypass -File .\towershell.ps1 install"
}

function Action-Install {
  Ensure-Dirs
  Ensure-Venv
  Pip-InstallBase
  Write-Host "OK"
}

function Action-Run {
  $venvPy = Get-VenvPython
  $entry = "app\main.py"
  if (-not (Test-Path $entry)) { throw "Missing $entry." }
  Write-Section "Running GUI"
  Invoke-External "`"$venvPy`" $entry"
}

function Verify-Python([string]$Path) {
  $venvPy = Get-VenvPython
  Invoke-External "`"$venvPy`" -m py_compile `"$Path`""
}

function Verify-Json([string]$Path) {
  try {
    Get-Content -Raw -Path $Path | ConvertFrom-Json | Out-Null
  } catch {
    throw "Invalid JSON: $Path"
  }
}

function Action-Verify([string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path)) { throw "verify requires a file path" }
  if (-not (Test-Path $Path)) { throw "File not found: $Path" }

  $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
  Write-Section "Verifying $Path"

  switch ($ext) {
    ".py" { Verify-Python $Path; break }
    ".json" { Verify-Json $Path; break }
    default { Write-Host "No verifier for $ext (OK)"; break }
  }

  Write-Host "OK"
}

function Action-Test {
  $venvPy = Get-VenvPython
  Write-Section "Running tests"
  Invoke-External "`"$venvPy`" -m pytest -q"
}

function Action-Format {
  $venvPy = Get-VenvPython
  Write-Section "Formatting (black)"
  Invoke-External "`"$venvPy`" -m black app tests"
}

function Action-Lint {
  $venvPy = Get-VenvPython
  Write-Section "Linting (ruff)"
  Invoke-External "`"$venvPy`" -m ruff check app tests"
}

function Action-Build {
  $venvPy = Get-VenvPython
  $entry = "app\main.py"
  if (-not (Test-Path $entry)) { throw "Missing $entry." }

  Write-Section "Building distributable (PyInstaller)"
  Invoke-External "`"$venvPy`" -m PyInstaller --noconfirm --clean --name LocalAISWE --windowed --onefile $entry"
  Write-Host "Output: dist\LocalAISWE.exe"
}

switch ($Action) {
  "help"    { Action-Help; break }
  "init"    { Action-Init; break }
  "install" { Action-Install; break }
  "run"     { Action-Run; break }
  "verify"  { Action-Verify $Arg1; break }
  "test"    { Action-Test; break }
  "format"  { Action-Format; break }
  "lint"    { Action-Lint; break }
  "build"   { Action-Build; break }
  default   { Action-Help; break }
}
