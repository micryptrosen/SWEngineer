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

function Resolve-ProjectRoot { (Get-Location).Path }

function Get-SystemPython {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return @("python", @()) }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return @("py", @("-3")) }

  throw "Python not found. Install Python 3.11+ and ensure it's on PATH."
}

function Escape-Arg([string]$s) {
  if ($null -eq $s) { return '""' }
  if ($s -match '[\s"]') {
    return '"' + ($s -replace '"', '\"') + '"'
  }
  return $s
}

function Invoke-Process(
  [string]$FilePath,
  [string[]]$ProcArgs,
  [string]$WorkingDir,
  [int]$TimeoutSec = 30
) {
  if ($null -eq $ProcArgs) { $ProcArgs = @() }

  $argText = ($ProcArgs | ForEach-Object { Escape-Arg $_ }) -join " "
  Write-Host "> $(Escape-Arg $FilePath) $argText"

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $FilePath
  $psi.Arguments = $argText
  $psi.WorkingDirectory = $WorkingDir
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.RedirectStandardInput = $true
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  try { $p.StandardInput.Close() } catch {}

  if (-not $p.WaitForExit($TimeoutSec * 1000)) {
    try { $p.Kill() } catch {}
    throw "Command timed out after $TimeoutSec seconds: $FilePath $argText"
  }

  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()

  if ($stdout) { Write-Host $stdout }
  if ($stderr) { Write-Host $stderr }

  if ($p.ExitCode -ne 0) {
    throw "Command failed with exit code $($p.ExitCode): $FilePath $argText"
  }
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
  $venvPy = Join-Path $root ".venv\Scripts\python.exe"
  if (Test-Path $venvPy) { return }

  Write-Section "Creating venv (.venv)"
  $pyInfo = Get-SystemPython
  $exe = $pyInfo[0]
  $prefix = $pyInfo[1]
  Invoke-Process $exe ($prefix + @("-m", "venv", ".venv")) $root 180

  if (-not (Test-Path $venvPy)) {
    throw "Venv created but python.exe not found at: $venvPy"
  }
}

function Get-VenvPython {
  $root = Resolve-ProjectRoot
  $venvPy = Join-Path $root ".venv\Scripts\python.exe"
  if (-not (Test-Path $venvPy)) { throw "Missing venv python at $venvPy. Run: .\towershell.ps1 init" }
  return $venvPy
}

function Pip-InstallBase {
  $root = Resolve-ProjectRoot
  $venvPy = Get-VenvPython

  Write-Section "Installing dependencies"
  Invoke-Process $venvPy @("-m","pip","install","--upgrade","pip","wheel","setuptools") $root 300

  $req = Join-Path $root "requirements.txt"
  if (Test-Path $req) {
    Invoke-Process $venvPy @("-m","pip","install","-r","requirements.txt") $root 900
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
  Invoke-Process $venvPy (@("-m","pip","install") + $pkgs) $root 900
}

function Action-Help {
@"
towershell.ps1

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
}

function Action-Install {
  Ensure-Dirs
  Ensure-Venv
  Pip-InstallBase
  Write-Host "OK"
}

function Action-Run {
  $root = Resolve-ProjectRoot
  $venvPy = Get-VenvPython
  $entry = Join-Path $root "app\main.py"
  if (-not (Test-Path $entry)) { throw "Missing app\main.py" }
  Write-Section "Running GUI"
  Invoke-Process $venvPy @($entry) $root 60
}

function Verify-Python([string]$Path) {
  $root = Resolve-ProjectRoot
  $venvPy = Get-VenvPython
  Invoke-Process $venvPy @("-m","py_compile",$Path) $root 20
}

function Verify-Json([string]$Path) {
  try { Get-Content -Raw -Path $Path | ConvertFrom-Json | Out-Null }
  catch { throw "Invalid JSON: $Path" }
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
  $root = Resolve-ProjectRoot
  $venvPy = Get-VenvPython
  Write-Section "Running tests"
  Invoke-Process $venvPy @("-m","pytest","-q") $root 300
}

function Action-Format {
  $root = Resolve-ProjectRoot
  $venvPy = Get-VenvPython
  Write-Section "Formatting (black)"
  Invoke-Process $venvPy @("-m","black","app","tests") $root 300
}

function Action-Lint {
  $root = Resolve-ProjectRoot
  $venvPy = Get-VenvPython
  Write-Section "Linting (ruff)"
  Invoke-Process $venvPy @("-m","ruff","check","app","tests") $root 300
}

function Action-Build {
  $root = Resolve-ProjectRoot
  $venvPy = Get-VenvPython
  $entry = Join-Path $root "app\main.py"
  if (-not (Test-Path $entry)) { throw "Missing app\main.py" }

  Write-Section "Building distributable (PyInstaller)"
  Invoke-Process $venvPy @(
    "-m","PyInstaller",
    "--noconfirm","--clean",
    "--name","LocalAISWE",
    "--windowed","--onefile",
    $entry
  ) $root 1200

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
