.PHONY: setup test lint run headless-short headless-long headless-adversarial headless-mixed clean

VENV      := .venv
PYTHON    := $(VENV)/bin/python
PIP       := $(VENV)/bin/pip
LOCUST    := $(VENV)/bin/locust
PYTEST    := $(VENV)/bin/pytest
RUFF      := $(VENV)/bin/ruff

setup:
	python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example — set RUNNER_KEY"; fi

test:
	$(PYTEST) tests/unit/ -v

lint:
	$(RUFF) check locust/ tests/

run:
	$(LOCUST) -f locust/locustfile.py

headless-short:
	$(LOCUST) -f locust/locustfile.py ShortConversationUser \
		--headless --users 20 --spawn-rate 2 --run-time 10m

headless-long:
	$(LOCUST) -f locust/locustfile.py LongConversationUser \
		--headless --users 5 --spawn-rate 1 --run-time 30m

headless-adversarial:
	$(LOCUST) -f locust/locustfile.py AdversarialUser \
		--headless --users 10 --spawn-rate 2 --run-time 10m

headless-mixed:
	$(LOCUST) -f locust/locustfile.py RealisticMixedUser \
		--headless --users 30 --spawn-rate 3 --run-time 15m

clean:
	rm -rf reports/*.html reports/*.csv reports/*.log reports/*.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
