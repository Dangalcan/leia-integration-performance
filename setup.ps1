# Windows PowerShell setup script
# Creates venv, installs deps, copies .env.example if .env missing

$ErrorActionPreference = "Stop"
$venvPath = ".\venv"

Write-Host "Creating virtual environment..."
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
} else {
    Write-Host "  venv already exists, skipping creation"
}

Write-Host "Installing dependencies..."
& "$venvPath\Scripts\pip.exe" install --upgrade pip --quiet
& "$venvPath\Scripts\pip.exe" install -r requirements.txt

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host ""
    Write-Host "Created .env from .env.example"
    Write-Host "IMPORTANT: Edit .env and set RUNNER_KEY before running tests"
} else {
    Write-Host ".env already exists"
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Activate venv:  .\venv\Scripts\Activate.ps1"
Write-Host "Run tests:      locust -f locust\locustfile.py"
