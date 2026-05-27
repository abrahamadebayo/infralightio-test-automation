#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[x]${NC} $*"; }

REPORT_DIR="$SCRIPT_DIR/reports"
mkdir -p "$REPORT_DIR"

# ── Check prerequisites ──────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || { err "docker is required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { err "python3 is required"; exit 1; }

# ── Copy .env if missing ─────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    log "Created .env from .env.example"
fi

# ── Install Python dependencies ──────────────────────────────────────
log "Installing Python dependencies..."
python3 -m pip install --quiet -e . 2>&1 | tail -1

# ── Start the API service ────────────────────────────────────────────
log "Starting API service..."
docker compose up -d --wait 2>&1

log "Waiting for API to be healthy..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8080/swagger/doc.json > /dev/null 2>&1; then
        log "API is ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        err "API failed to start within 90 seconds"
        docker compose logs
        exit 1
    fi
    sleep 3
done

# ── Run tests ────────────────────────────────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/report_${TIMESTAMP}.html"

log "Running test suite..."
python3 -m pytest tests/ \
    --ignore=tests/load \
    --html="$REPORT_FILE" \
    --self-contained-html \
    -v \
    --tb=short \
    "$@" \
    || true

cp "$REPORT_FILE" "$REPORT_DIR/report.html"
log "Test report: $REPORT_FILE"

# ── Optional: run Locust load test ───────────────────────────────────
if [ "${RUN_LOAD_TEST:-false}" = "true" ]; then
    LOAD_REPORT="$REPORT_DIR/load_${TIMESTAMP}.html"
    log "Running load tests..."
    python3 -m pytest tests/load/ \
        --html="$LOAD_REPORT" \
        --self-contained-html \
        -v \
        --tb=short \
        || true
    log "Load test report: $LOAD_REPORT"

    LOCUST_REPORT="$REPORT_DIR/locust_${TIMESTAMP}.html"
    log "Running Locust load test (60s)..."
    python3 -m locust \
        -f locustfile.py \
        --headless \
        -u "${LOAD_TEST_USERS:-10}" \
        -r "${LOAD_TEST_SPAWN_RATE:-2}" \
        -t "${LOAD_TEST_DURATION:-60}s" \
        --host http://localhost:8080 \
        --html "$LOCUST_REPORT" \
        2>&1 | tail -5
    log "Locust report: $LOCUST_REPORT"
fi

# ── Cleanup ──────────────────────────────────────────────────────────
log "Stopping API service..."
docker compose down 2>&1

log "Done. Reports are in $REPORT_DIR/"
