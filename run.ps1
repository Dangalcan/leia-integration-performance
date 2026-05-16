<#
.SYNOPSIS
    Windows equivalent of the Makefile. Runs Locust scenarios from PowerShell,
    where localhost:9000 resolves to Windows host directly (no WSL networking issues).

.EXAMPLE
    .\run.ps1                       # web UI mode
    .\run.ps1 headless-short        # headless, ShortConversationUser
    .\run.ps1 headless-mixed        # headless, RealisticMixedUser
    .\run.ps1 setup                 # create venv and install deps
#>
param(
    [Parameter(Position = 0)]
    [string]$Target = "run"
)

$venvRoot = ".\venv"
$locust   = "$venvRoot\Scripts\locust.exe"
$pytest   = "$venvRoot\Scripts\pytest.exe"
$ruff     = "$venvRoot\Scripts\ruff.exe"

$noVenvTargets = @("setup", "clean")

if ($noVenvTargets -notcontains $Target -and -not (Test-Path $locust)) {
    Write-Error "venv not found. Run first: .\run.ps1 setup"
    exit 1
}

# Load .env into process environment
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -match "^\s*[^#\s].*=" } | ForEach-Object {
        $parts = $_ -split "=", 2
        if ($parts.Count -eq 2) {
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

$f = "locust\locustfile.py"

switch ($Target) {
    "run"                  { & $locust -f $f }
    "headless-short"       { & $locust -f $f ShortConversationUser --headless --users 20 --spawn-rate 2 --run-time 10m }
    "headless-long"        { & $locust -f $f LongConversationUser  --headless --users 5  --spawn-rate 1 --run-time 30m }
    "headless-adversarial" { & $locust -f $f AdversarialUser       --headless --users 10 --spawn-rate 2 --run-time 10m }
    "headless-mixed"       { & $locust -f $f RealisticMixedUser    --headless --users 30 --spawn-rate 3 --run-time 15m }
    "test"                 { & $pytest tests\unit\ -v }
    "lint"                 { & $ruff check locust\ tests\ }
    "clean" {
        Remove-Item reports\*.html, reports\*.csv, reports\*.log, reports\*.json -ErrorAction SilentlyContinue
        Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
    }
    "setup" { & .\setup.ps1 }
    default {
        Write-Error "Unknown target '$Target'. Valid: run, headless-short, headless-long, headless-adversarial, headless-mixed, test, lint, clean, setup"
        exit 1
    }
}
