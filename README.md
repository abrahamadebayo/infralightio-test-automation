# QA Test API — Test Automation

Automated test suite for the QA Test API (`infralightio/test-integration-api`).

## Results

- **87 tests**: 52 passed, 35 failed (0 errors)
- **29 bugs found** across 8 test categories — see [TEST_PLAN.md](TEST_PLAN.md) for the full bug report
- Key findings: critical tenant isolation failures, server crash on PATCH with invalid data, resource leak after ~35 requests

## Prerequisites

- Docker (with Docker Compose)
- Python 3.10+

## Quick Start

```bash
./run.sh
```

This single command will:
1. Install Python dependencies
2. Start the API in Docker
3. Run the full test suite
4. Generate an HTML report in `reports/`
5. Stop the API container

## Run with Load Testing

```bash
RUN_LOAD_TEST=true ./run.sh
```

## Manual Execution

```bash
# Start the API
docker compose up -d --wait

# Install deps
pip install -e .

# Run all tests
pytest

# Run by folder
pytest tests/crud/             # CRUD operations
pytest tests/security/         # Auth + tenant isolation
pytest tests/contract/         # OpenAPI contract validation
pytest tests/pagination/       # Pagination behavior
pytest tests/validation/       # Input validation
pytest tests/load/             # Load/performance tests

# Run by marker
pytest -m smoke          # Core functionality
pytest -m crud           # CRUD operations
pytest -m tenant         # Tenant isolation

# Generate HTML report
pytest --html=reports/report.html --self-contained-html

# Stop the API
docker compose down
```

## Standalone Locust Load Test

```bash
locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8080 --html reports/locust.html
```

## Project Structure

```
├── run.sh                      # Single-command execution
├── docker-compose.yml          # API service definition
├── pyproject.toml              # Python project & pytest config
├── .env.example                # Configuration template
├── locustfile.py               # Locust load test definition
├── TEST_PLAN.md                # Test plan & bug report
├── src/
│   ├── client/
│   │   ├── http.py             # CurlResponse, low-level HTTP via subprocess+curl
│   │   └── api.py              # APIClient, UnauthenticatedClient
│   ├── config/
│   │   └── settings.py         # Settings, UserCredentials, env loading
│   └── models/
│       ├── enums.py            # IntegrationType, HttpStatus, EXPECTED_STATUS
│       └── responses.py        # Pydantic response models (Integration, Asset, etc.)
└── tests/
    ├── conftest.py             # Global fixtures, factories, auto-restart logic
    ├── helpers.py              # Shared test utilities (unique_name)
    ├── crud/
    │   ├── test_integrations.py    # Integration CRUD
    │   └── test_assets.py          # Asset CRUD
    ├── security/
    │   ├── test_auth.py            # Authentication enforcement
    │   └── test_tenant_isolation.py # Tenant segregation
    ├── contract/
    │   └── test_contract.py        # OpenAPI contract validation
    ├── pagination/
    │   └── test_pagination.py      # Pagination behavior
    ├── validation/
    │   └── test_validation.py      # Input validation
    └── load/
        └── test_load.py            # Load/throughput tests
```

## Configuration

Copy `.env.example` to `.env` and adjust values as needed. The run script does this automatically if `.env` is missing.

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8080` | API host |
| `API_BASE_PATH` | `/api/v1` | API path prefix |
| `USER1_USERNAME` | `test1` | First test user |
| `USER1_PASSWORD` | `test123` | First test password |
| `USER2_USERNAME` | `test2` | Second test user |
| `USER2_PASSWORD` | `test456` | Second test password |
| `LOAD_TEST_TARGET_RPM` | `1000` | Load test target (requests/min) |
