#!/usr/bin/env bash
set -euo pipefail

echo "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
else
    echo "  .venv already exists, skipping creation"
fi

echo "Installing dependencies..."
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from .env.example"
    echo "IMPORTANT: Edit .env and set RUNNER_KEY before running tests"
else
    echo ".env already exists"
fi

echo ""
echo "Setup complete."
echo "Activate venv:  source .venv/bin/activate"
echo "Run tests:      locust -f locust/locustfile.py"
