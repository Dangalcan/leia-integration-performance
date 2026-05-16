# leia-integration-performance

Locust-based performance test suite for [leia-runner](../leia/leia-runner). Replays 37 real ALMA conversation recordings to simulate realistic concurrent load.

## Prerequisites

- Python 3.10+ (3.11 recommended)
- leia-runner running (see its README)

## Setup

**Windows:**
```powershell
.\setup.ps1
.\.venv\Scripts\Activate.ps1
```

**Unix / Make:**
```bash
make setup
source .venv/bin/activate
```

**Docker:**
```bash
docker compose up
# open http://localhost:8089
```

Then edit `.env` — it is pre-filled with defaults but verify `TARGET_HOST` and `RUNNER_KEY` match your leia-runner instance.

## Running tests

### Web UI (recommended for exploration)
```bash
locust -f locust/locustfile.py
```
Open **http://localhost:8089**, set user count and spawn rate, press **Start**.

### Headless (CI / scripted)
```bash
locust -f locust/locustfile.py --headless --users 20 --spawn-rate 2 --run-time 10m
```

### Make shortcuts
```bash
make headless-short       # 20 users, 10m — ShortConversationUser
make headless-long        # 5 users,  30m — LongConversationUser
make headless-adversarial # 10 users, 10m — AdversarialUser
make headless-mixed       # 30 users, 15m — RealisticMixedUser
```

### Run a specific scenario
```bash
locust -f locust/locustfile.py ShortConversationUser
locust -f locust/locustfile.py LongConversationUser
locust -f locust/locustfile.py AdversarialUser
locust -f locust/locustfile.py RealisticMixedUser
```

## Scenarios

| Scenario | Session pool | Rec. users | Rec. run-time | Best for |
|---|---|---|---|---|
| `ShortConversationUser` | ec ≤ SHORT\_MAX\_EXCHANGES (14 sessions) | 20 | 10m | High-concurrency baseline |
| `LongConversationUser` | ec ≥ LONG\_MIN\_EXCHANGES (3 sessions) | 5 | 30m | Sustained load, memory/state |
| `AdversarialUser` | Injection patterns (4 sessions) | 10 | 10m | Error handling, refusals |
| `RealisticMixedUser` | All 37 (weighted) | 30 | 15m | Production simulation |

## Configuration

### Core variables

| Variable | Default | Description |
|---|---|---|
| `TARGET_HOST` | `http://localhost:9000` | leia-runner base URL |
| `RUNNER_KEY` | — | Bearer token (leia-runner `RUNNER_KEY`) |
| `DEFAULT_PROVIDER` | `alma` | AI provider for new LEIA instances |
| `MAX_THINK_TIME_SECONDS` | `120` | Cap on inter-exchange think time |
| `SESSIONS_DIR` | `./sessions` | Path to session JSON recordings |

### LEIA spec

| Variable | Default | Description |
|---|---|---|
| `LEIA_INSTANCE_ID` | `leia-perf-test` | Prefix for generated LEIA instance IDs |
| `LEIA_SPEC_FILE` | — | Path to JSON file overriding built-in LEIA spec |

The built-in spec encodes the theater-ticket-platform experiment. To override, create a JSON file:
```json
{
  "leia_id": "my-leia",
  "description": "{replication_name} — your tutor description",
  "solution": "student provides X",
  "solution_format": "text",
  "evaluation_prompt": "evaluate if the student did Y"
}
```
Then set `LEIA_SPEC_FILE=path/to/spec.json`.

### Timing & resilience

| Variable | Default | Description |
|---|---|---|
| `BURST_GAP_CAP_MS` | `5000` | Max ms between messages within a burst |
| `REQUEST_TIMEOUT_SECONDS` | `60` | HTTP timeout for all leia-runner calls |
| `RETRY_MAX` | `2` | Retries for send\_message on 5xx/network error |
| `CONTINUE_ON_MESSAGE_FAILURE` | `false` | If true, skip failed message and continue session |

### Classification thresholds

| Variable | Default | Description |
|---|---|---|
| `SHORT_MAX_EXCHANGES` | `12` | exchange\_count ≤ N → "short" |
| `LONG_MIN_EXCHANGES` | `20` | exchange\_count ≥ N → "long" |

### Observability

| Variable | Default | Description |
|---|---|---|
| `PERCENTILES` | `50,90,99` | Percentiles in console summary and JSON export |
| `PREFLIGHT_CHECK` | `false` | Fire GET /api/v1/models before test to verify connectivity |

## Reports

After each run, `reports/` contains:
- `locust_report.html` — interactive Locust report
- `locust_results_*.csv` — request stats and failures
- `locust.log` — full log output
- `ai_latency_summary.json` — per-scenario statistics (count, min, max, mean, stdev, P50/P90/P99)

### Interpreting the JSON summary

```json
{
  "generated_at": "2025-05-15T10:30:00",
  "scenarios": {
    "short": {
      "count": 856,
      "min": 1200.0,
      "max": 28400.0,
      "mean": 5800.0,
      "stdev": 3200.0,
      "p50": 5100.0,
      "p90": 9800.0,
      "p99": 18200.0
    }
  }
}
```

All times are in milliseconds. Percentiles use linear interpolation (same as numpy/pandas default).

## Weight distribution in RealisticMixedUser

Sessions are sampled with weights that approximate the observed ALMA production mix:

| Class | Target probability | Sessions |
|---|---|---|
| short | 40% | 14 |
| medium | 43% | 16 |
| long | 11% | 3 |
| adversarial | 6% | 4 |

Each session within a class receives `class_prob / session_count` weight. The sum of all weights equals 1.0.

## Session data

37 JSON recordings in `sessions/` captured from real ALMA usage. Each file:
- Name: `{session-id}__{env}.json` (env = `prod` or `pre`)
- Contains: user/assistant messages with timestamps, response times per exchange, session metadata

Sessions are classified automatically at startup. Classification counts printed on init:
```
Sessions loaded: 37 total — short=14  medium=16  long=3  adversarial=4
```

## Development

```bash
make test    # run unit tests
make lint    # ruff check
```

Unit tests cover: percentile correctness, thread-safe metric accumulation, session classification, exchange building, config validation.

## Project structure

```
locust/
├── locustfile.py        # Entry point, init/stop hooks
├── config.py            # Reads .env, validate_config()
├── core/
│   ├── base_scenario.py   # Shared replay loop (BaseReplayUser)
│   ├── session_loader.py  # Parses and classifies sessions
│   ├── leia_client.py     # API call helpers (timeout, retry)
│   └── metrics.py         # Custom Locust events, JSON export
└── scenarios/
    ├── short_conversation.py
    ├── long_conversation.py
    ├── adversarial.py
    └── realistic_mixed.py
tests/
├── conftest.py
└── unit/
    ├── test_metrics.py
    ├── test_session_loader.py
    └── test_config.py
```
